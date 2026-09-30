"""Differential parity for reconciliation orchestration through a fake port."""

from __future__ import annotations

import ast
from dataclasses import asdict
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.dispatch_models import ExecutionState
from bot_spx.execution.reconciliation_service import refresh_broker_reconciliation
from tests.characterization.legacy_harness import (
    DeterministicBrokerLookup,
    load_refresh_broker_reconciliation,
)


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "reconciliation_service.py"
)
PORT_PATH = SERVICE_PATH.with_name("broker_lookup.py")
INITIAL_STATE = ExecutionState(
    broker_account_id="SENTINEL-ACCOUNT",
    broker_position_available=False,
    broker_position_reason="SENTINEL_BROKER_POSITION_REASON",
    position_reconciliation_ok=False,
    position_reconciliation_action="SENTINEL_ACTION",
    position_reconciliation_reason="SENTINEL_RECONCILIATION_REASON",
    broker_order_state="NONE",
    broker_order_id=None,
    broker_order_status="NONE",
    broker_order_status_description="NONE",
    dispatch_status="IDLE",
    dispatch_reason="NO EXECUTION REQUEST",
    dispatch_id=None,
    position_state="FLAT",
    position_contracts=0,
    position_entry_side="NONE",
    last_dispatch_signature=None,
    pending_order_action="NONE",
    pending_order_side="NONE",
    pending_order_quantity=0,
    pending_order_symbol=None,
    pending_order_submitted_at=None,
)
RECONCILIATION_FIELDS = {
    "broker_account_id": "CURRENT_BROKER_ACCOUNT_ID",
    "broker_position_available": "CURRENT_BROKER_POSITION_AVAILABLE",
    "broker_position_reason": "CURRENT_BROKER_POSITION_REASON",
    "position_reconciliation_ok": "CURRENT_POSITION_RECONCILIATION_OK",
    "position_reconciliation_action": "CURRENT_POSITION_RECONCILIATION_ACTION",
    "position_reconciliation_reason": "CURRENT_POSITION_RECONCILIATION_REASON",
}


@pytest.mark.parametrize(
    (
        "case",
        "internal_changes",
        "account_id",
        "account_reason",
        "position_result",
        "expected_position_calls",
    ),
    [
        (
            "account-unavailable",
            {},
            None,
            "SYNTHETIC ACCOUNT UNAVAILABLE",
            {"ok": True, "position": None},
            0,
        ),
        (
            "position-lookup-failed",
            {},
            "SYNTHETIC-ACCOUNT",
            "SYNTHETIC ACCOUNT AVAILABLE",
            {"ok": False, "reason": "SYNTHETIC POSITION LOOKUP FAILURE"},
            1,
        ),
        (
            "flat-match",
            {},
            "SYNTHETIC-ACCOUNT",
            "SYNTHETIC ACCOUNT AVAILABLE",
            {"ok": True, "position": None},
            1,
        ),
        (
            "long-match",
            {"position_state": "LONG", "position_contracts": 3, "position_entry_side": "BUY"},
            "SYNTHETIC-ACCOUNT",
            "SYNTHETIC ACCOUNT AVAILABLE",
            {"ok": True, "position": {"Quantity": 3}},
            1,
        ),
        (
            "short-match",
            {"position_state": "SHORT", "position_contracts": 3, "position_entry_side": "SELL"},
            "SYNTHETIC-ACCOUNT",
            "SYNTHETIC ACCOUNT AVAILABLE",
            {"ok": True, "position": {"Quantity": -3}},
            1,
        ),
        (
            "broker-unknown",
            {},
            "SYNTHETIC-ACCOUNT",
            "SYNTHETIC ACCOUNT AVAILABLE",
            {"ok": True, "position": {"Quantity": "ABC"}},
            1,
        ),
        (
            "known-mismatch-blocks",
            {},
            "SYNTHETIC-ACCOUNT",
            "SYNTHETIC ACCOUNT AVAILABLE",
            {"ok": True, "position": {"Quantity": 2}},
            1,
        ),
    ],
)
def test_reconciliation_service_matches_phase4_oracle(
    case: str,
    internal_changes: dict[str, object],
    account_id: str | None,
    account_reason: str,
    position_result: dict[str, object],
    expected_position_calls: int,
) -> None:
    state = ExecutionState(**(asdict(INITIAL_STATE) | internal_changes))
    oracle = load_refresh_broker_reconciliation(
        position_state=state.position_state,
        position_contracts=state.position_contracts,
        position_entry_side=state.position_entry_side,
        broker_account_id=state.broker_account_id,
        broker_position_available=state.broker_position_available,
        broker_position_reason=state.broker_position_reason,
        reconciliation_ok=state.position_reconciliation_ok,
        reconciliation_action=state.position_reconciliation_action,
        reconciliation_reason=state.position_reconciliation_reason,
        lookup_account_id=account_id,
        lookup_account_reason=account_reason,
        lookup_position_result=position_result,
    )
    candidate_lookup = DeterministicBrokerLookup(
        account_id,
        account_reason,
        position_result,
    )

    oracle_result = oracle.function()
    candidate = refresh_broker_reconciliation(state, candidate_lookup)
    candidate_values = asdict(candidate.state)

    assert candidate.result == oracle_result, case
    for candidate_name, oracle_name in RECONCILIATION_FIELDS.items():
        assert candidate_values[candidate_name] == oracle.namespace[oracle_name], case
    for name, value in asdict(state).items():
        if name not in RECONCILIATION_FIELDS:
            assert candidate_values[name] == value, case
    assert oracle.lookup.account_call_count == candidate_lookup.account_call_count == 1
    assert oracle.lookup.position_call_count == expected_position_calls
    assert candidate_lookup.position_call_count == expected_position_calls
    assert oracle.lookup.position_account_ids == candidate_lookup.position_account_ids
    assert oracle.transport.call_count == 0


def test_reconciliation_service_signature_injects_port_explicitly() -> None:
    signature = inspect.signature(refresh_broker_reconciliation)

    assert list(signature.parameters) == ["state", "broker_lookup"]


@pytest.mark.parametrize("path", [SERVICE_PATH, PORT_PATH])
def test_reconciliation_port_and_service_have_no_external_capability(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))

    for forbidden_reference in (
        "requests",
        "http",
        "tradestation_request",
        "token",
        "credential",
        "dotenv",
    ):
        assert forbidden_reference not in source.lower()
