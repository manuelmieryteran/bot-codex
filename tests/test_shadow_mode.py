"""Isolated shadow-mode bridge, parity, and null-submit guarantees."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from bot_spx.execution.dispatch_models import ExecutionState
from bot_spx.execution.shadow_bridge import (
    execution_config_from_legacy,
    execution_intent_from_legacy,
    execution_state_from_legacy,
)
from bot_spx.execution.shadow_mode import run_dispatch_shadow
from bot_spx.execution.shadow_submit import NullOrderSubmitPort
from tests.characterization.legacy_harness import (
    FIXED_PENDING_TIMESTAMP,
    SYNTHETIC_SUBMIT_FAILURE,
    SYNTHETIC_SUBMIT_SUCCESS,
    load_dispatch_execution_category_a,
    load_dispatch_execution_category_b_failure,
    load_dispatch_execution_category_b_success,
)


ROOT = Path(__file__).resolve().parents[1]
INITIAL_SIGNATURE = ("PREVIOUS", "NONE", 99, "PREVIOUS REASON")


def _legacy_values(**changes: object) -> dict[str, object]:
    values = {
        "CURRENT_BROKER_ACCOUNT_ID": "SYNTHETIC-ACCOUNT",
        "CURRENT_BROKER_POSITION_AVAILABLE": True,
        "CURRENT_BROKER_POSITION_REASON": "SYNTHETIC BROKER POSITION",
        "CURRENT_POSITION_RECONCILIATION_OK": True,
        "CURRENT_POSITION_RECONCILIATION_ACTION": "ALLOW",
        "CURRENT_POSITION_RECONCILIATION_REASON": "SYNTHETIC MATCH",
        "CURRENT_BROKER_ORDER_STATE": "NONE",
        "CURRENT_BROKER_ORDER_ID": None,
        "CURRENT_BROKER_ORDER_STATUS": "NONE",
        "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION": "NONE",
        "CURRENT_DISPATCH_STATUS": "SENTINEL_DISPATCH_STATUS",
        "CURRENT_DISPATCH_REASON": "SENTINEL_DISPATCH_REASON",
        "CURRENT_DISPATCH_ID": "SENTINEL_DISPATCH_ID",
        "CURRENT_POSITION_STATE": "FLAT",
        "CURRENT_POSITION_CONTRACTS": 0,
        "CURRENT_POSITION_ENTRY_SIDE": "NONE",
        "LAST_DISPATCH_SIGNATURE": INITIAL_SIGNATURE,
        "CURRENT_PENDING_ORDER_ACTION": "SENTINEL_ACTION",
        "CURRENT_PENDING_ORDER_SIDE": "SENTINEL_SIDE",
        "CURRENT_PENDING_ORDER_QUANTITY": 91,
        "CURRENT_PENDING_ORDER_SYMBOL": "SENTINEL_SYMBOL",
        "CURRENT_PENDING_ORDER_SUBMITTED_AT": "SENTINEL_TIME",
        "CURRENT_EXECUTION_STATUS": "READY",
        "CURRENT_EXECUTION_ACTION": "ENTRY",
        "CURRENT_EXECUTION_SIDE": "BUY",
        "CURRENT_EXECUTION_QUANTITY": 2,
        "CURRENT_EXECUTION_SYMBOL": "SYNTHETIC-ES",
        "CURRENT_EXECUTION_ORDER_TYPE": "MARKET",
        "CURRENT_EXECUTION_REASON": "LONG MEAN REVERSION",
        "EXECUTION_MODE": "LIVE",
        "LIVE_ORDER_EXECUTION_ENABLED": True,
    }
    return values | changes


def _oracle_state(values: dict[str, object], namespace: dict[str, object]):
    after = values | {
        name: namespace[name]
        for name in (
            "CURRENT_BROKER_ORDER_STATE",
            "CURRENT_POSITION_STATE",
            "CURRENT_POSITION_CONTRACTS",
            "CURRENT_POSITION_ENTRY_SIDE",
            "LAST_DISPATCH_SIGNATURE",
            "CURRENT_PENDING_ORDER_ACTION",
            "CURRENT_PENDING_ORDER_SIDE",
            "CURRENT_PENDING_ORDER_QUANTITY",
            "CURRENT_PENDING_ORDER_SYMBOL",
            "CURRENT_PENDING_ORDER_SUBMITTED_AT",
        )
    }
    return execution_state_from_legacy(after)


def _load_category_a(values: dict[str, object]):
    return load_dispatch_execution_category_a(
        execution_status=values["CURRENT_EXECUTION_STATUS"],
        execution_action=values["CURRENT_EXECUTION_ACTION"],
        execution_side=values["CURRENT_EXECUTION_SIDE"],
        execution_quantity=values["CURRENT_EXECUTION_QUANTITY"],
        execution_symbol=values["CURRENT_EXECUTION_SYMBOL"],
        execution_order_type=values["CURRENT_EXECUTION_ORDER_TYPE"],
        execution_reason=values["CURRENT_EXECUTION_REASON"],
        broker_order_state=values["CURRENT_BROKER_ORDER_STATE"],
        position_state=values["CURRENT_POSITION_STATE"],
        position_contracts=values["CURRENT_POSITION_CONTRACTS"],
        position_entry_side=values["CURRENT_POSITION_ENTRY_SIDE"],
        execution_mode=values["EXECUTION_MODE"],
        live_order_execution_enabled=values["LIVE_ORDER_EXECUTION_ENABLED"],
        position_reconciliation_ok=values["CURRENT_POSITION_RECONCILIATION_OK"],
        last_dispatch_signature=values["LAST_DISPATCH_SIGNATURE"],
        pending_order_action=values["CURRENT_PENDING_ORDER_ACTION"],
        pending_order_side=values["CURRENT_PENDING_ORDER_SIDE"],
        pending_order_quantity=values["CURRENT_PENDING_ORDER_QUANTITY"],
        pending_order_symbol=values["CURRENT_PENDING_ORDER_SYMBOL"],
        pending_order_submitted_at=values["CURRENT_PENDING_ORDER_SUBMITTED_AT"],
        broker_account_id=values["CURRENT_BROKER_ACCOUNT_ID"],
    )


def test_bridge_captures_explicit_legacy_snapshot_without_mutation() -> None:
    values = _legacy_values()
    before = dict(values)

    state = execution_state_from_legacy(values)
    intent = execution_intent_from_legacy(values)
    config = execution_config_from_legacy(values, submission_timestamp=None)

    assert state.position_state == "FLAT"
    assert state.broker_account_id == "SYNTHETIC-ACCOUNT"
    assert intent.reason == "LONG MEAN REVERSION"
    assert config.execution_mode == "LIVE"
    assert config.submission_timestamp is None
    assert values == before


@pytest.mark.parametrize(
    "changes",
    [
        {"CURRENT_EXECUTION_STATUS": "IDLE"},
        {"CURRENT_BROKER_ORDER_STATE": "OPEN"},
        {
            "EXECUTION_MODE": "DRY_RUN",
            "LIVE_ORDER_EXECUTION_ENABLED": False,
        },
        {"CURRENT_POSITION_RECONCILIATION_OK": False},
        {"CURRENT_BROKER_ACCOUNT_ID": None},
    ],
    ids=["idle", "broker-open", "dry-run", "safety-block", "payload-block"],
)
def test_shadow_category_a_matches_legacy_oracle(changes: dict[str, object]) -> None:
    values = _legacy_values(**changes)
    oracle = _load_category_a(values)
    legacy_result = oracle.function()
    port = NullOrderSubmitPort()

    shadow = run_dispatch_shadow(
        execution_state_from_legacy(values),
        execution_intent_from_legacy(values),
        execution_config_from_legacy(values, submission_timestamp=None),
        legacy_state=_oracle_state(values, oracle.namespace),
        legacy_result=legacy_result,
        submit_port=port,
    )

    assert shadow.candidate_accepted is True
    assert shadow.mismatches == ()
    assert shadow.legacy_result == legacy_result
    assert shadow.submit_record is None
    assert port.records == []
    assert oracle.transport.call_count == 0
    assert oracle.submit.call_count == 0


@pytest.mark.parametrize(
    ("loader", "submit_result"),
    [
        (load_dispatch_execution_category_b_failure, SYNTHETIC_SUBMIT_FAILURE),
        (load_dispatch_execution_category_b_success, SYNTHETIC_SUBMIT_SUCCESS),
    ],
    ids=["failure", "success"],
)
def test_shadow_submit_is_recorded_only_and_matches_observed_legacy_result(
    loader,
    submit_result: dict[str, object],
) -> None:
    values = _legacy_values()
    oracle = loader()
    legacy_result = oracle.function()
    port = NullOrderSubmitPort()

    shadow = run_dispatch_shadow(
        execution_state_from_legacy(values),
        execution_intent_from_legacy(values),
        execution_config_from_legacy(
            values,
            submission_timestamp=FIXED_PENDING_TIMESTAMP,
        ),
        legacy_state=_oracle_state(values, oracle.namespace),
        legacy_result=legacy_result,
        submit_port=port,
        observed_submit_result=submit_result,
    )

    assert shadow.candidate_accepted is True
    assert shadow.mismatches == ()
    assert shadow.submit_record == port.records[0]
    assert shadow.submit_record.kind == "SUBMIT_ORDER"
    assert shadow.submit_record.payload == oracle.submit.payloads[0]
    assert len(port.records) == 1
    assert oracle.transport.call_count == 0


def test_missing_submit_observation_fails_candidate_closed() -> None:
    values = _legacy_values()
    legacy_result = {"status": "AUTHORITATIVE LEGACY RESULT"}
    state = execution_state_from_legacy(values)
    port = NullOrderSubmitPort()

    shadow = run_dispatch_shadow(
        state,
        execution_intent_from_legacy(values),
        execution_config_from_legacy(
            values,
            submission_timestamp=FIXED_PENDING_TIMESTAMP,
        ),
        legacy_state=state,
        legacy_result=legacy_result,
        submit_port=port,
    )

    assert shadow.candidate_accepted is False
    assert shadow.legacy_result is legacy_result
    assert [mismatch.field for mismatch in shadow.mismatches] == [
        "observed_submit_result"
    ]
    assert len(port.records) == 1


def test_mismatch_is_structured_and_never_changes_legacy_result() -> None:
    values = _legacy_values(CURRENT_EXECUTION_STATUS="IDLE")
    state = execution_state_from_legacy(values)
    legacy_result = {"status": "AUTHORITATIVE"}

    shadow = run_dispatch_shadow(
        state,
        execution_intent_from_legacy(values),
        execution_config_from_legacy(values, submission_timestamp=None),
        legacy_state=replace(state, position_state="LONG"),
        legacy_result=legacy_result,
        submit_port=NullOrderSubmitPort(),
    )

    assert shadow.candidate_accepted is False
    assert shadow.legacy_result is legacy_result
    assert {mismatch.field for mismatch in shadow.mismatches} == {
        "state",
        "result",
    }


def test_null_submit_and_shadow_modules_have_no_external_capability() -> None:
    paths = [
        ROOT / "src/bot_spx/execution/shadow_bridge.py",
        ROOT / "src/bot_spx/execution/shadow_mode.py",
        ROOT / "src/bot_spx/execution/shadow_submit.py",
    ]
    forbidden = {
        "requests",
        "urllib",
        "http",
        "socket",
        "dotenv",
        "tradestation",
        "sim_http_transport",
    }

    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imports = {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imports.update(
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert imports.isdisjoint(forbidden)

    assert not hasattr(NullOrderSubmitPort, "submit")
    assert not hasattr(NullOrderSubmitPort, "request")


def test_operational_baseline_does_not_import_shadow_modules() -> None:
    baseline = ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
    source = baseline.read_text(encoding="utf-8")

    assert "bot_spx.execution.shadow" not in source
