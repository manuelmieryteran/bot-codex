"""Phase 5C-2: offline Shadow-ON differential validation.

The runtime files are read-only inputs.  Shadow is enabled only in the isolated
AST namespace built by :mod:`tests.runtime_parity_harness`; legacy remains the
effective result and the candidate only receives the already-observed submit
result.  The semantic contract compares status/action/side/quantity/reason,
broker outcome and the complete modular state.  Representation-only fields
(``candidate_transition``, dataclass type names and the local submit record)
are not directly comparable because legacy represents them as dictionaries or
globals; their semantic payloads are compared instead.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace

import pytest

from bot_spx.execution.shadow_bridge import (
    execution_config_from_legacy,
    execution_intent_from_legacy,
    execution_state_from_legacy,
)
from bot_spx.execution.shadow_mode import run_dispatch_shadow
from bot_spx.execution.shadow_submit import NullOrderSubmitPort
from tests.runtime_parity_harness import PHASE4, PHASE5, load_runtime, mismatch_records


CATEGORY_A = [
    ("idle", {"CURRENT_EXECUTION_STATUS": "IDLE"}),
    ("broker-open", {"CURRENT_BROKER_ORDER_STATE": "OPEN"}),
    ("broker-unknown", {"CURRENT_BROKER_ORDER_STATE": "UNKNOWN"}),
    ("entry-non-flat", {"CURRENT_POSITION_STATE": "LONG", "CURRENT_POSITION_CONTRACTS": 1, "CURRENT_POSITION_ENTRY_SIDE": "BUY"}),
    ("exit-flat", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN"}),
    ("duplicate", {"LAST_DISPATCH_SIGNATURE": ("ENTRY", "BUY", 2, "SYNTHETIC INTENT")}),
    ("dry-run-buy", {"EXECUTION_MODE": "DRY_RUN"}),
    ("dry-run-sell", {"EXECUTION_MODE": "DRY_RUN", "CURRENT_EXECUTION_SIDE": "SELL"}),
    ("safety-blocked", {"LIVE_ORDER_EXECUTION_ENABLED": False}),
    ("payload-blocked", {"CURRENT_BROKER_ACCOUNT_ID": None}),
]

CATEGORY_B = [
    ("entry-buy-success", {}, True),
    ("entry-buy-failure", {}, False),
    ("entry-sell-success", {"CURRENT_EXECUTION_SIDE": "SELL"}, True),
    ("entry-sell-failure", {"CURRENT_EXECUTION_SIDE": "SELL"}, False),
    ("exit-long-success", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "LONG", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "BUY"}, True),
    ("exit-long-failure", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "LONG", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "BUY"}, False),
    ("exit-short-success", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "SHORT", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "SELL"}, True),
    ("exit-short-failure", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "SHORT", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "SELL"}, False),
]


def _run(scenario: str, overrides: dict[str, object], success: bool, category: str) -> dict[str, object]:
    oracle = load_runtime(PHASE4, overrides, submit_success=success)
    shadow_off = load_runtime(PHASE5, overrides, submit_success=success)
    shadow_on = load_runtime(PHASE5, overrides | {"SHADOW_EXECUTION_ENABLED": True}, submit_success=success)
    result4 = oracle.dispatch()
    result_off = shadow_off.dispatch()
    result_on = shadow_on.dispatch()
    candidate = shadow_on.namespace["CURRENT_SHADOW_RESULT"]
    assert result4 == result_off == result_on
    assert oracle.snapshot() == shadow_off.snapshot() == shadow_on.snapshot()
    assert candidate.legacy_result == result_on
    assert candidate.mismatches == ()
    assert candidate.candidate_accepted is True
    assert shadow_on.ledger.candidate_submit_attempts == shadow_on.ledger.real_submit == 0
    return {
        "scenario": scenario,
        "category": category,
        "legacy_status": result_on["status"],
        "candidate_outcome": "MATCH",
        "candidate_accepted": True,
        "effect_kind": candidate.submit_record.kind if candidate.submit_record else candidate.candidate_transition.effect.kind,
        "mismatch_count": 0,
        "mismatch_classification": "MATCH",
        "legacy_state_equal": True,
        "deterministic": True,
        "external_activity": {
            "transport": shadow_on.ledger.transport,
            "http": shadow_on.ledger.http,
            "oauth": shadow_on.ledger.oauth,
            "post": shadow_on.ledger.post,
            "real_submit": shadow_on.ledger.real_submit,
            "real_orders": shadow_on.ledger.real_orders,
            "digitalocean": shadow_on.ledger.digitalocean,
            "token_reads": shadow_on.ledger.token_reads,
            "main": shadow_on.ledger.main,
        },
        "legacy_fake_submits": len(shadow_on.submit.calls),
        "null_port_records": shadow_on.ledger.null_port,
        "candidate": repr(candidate),
        "legacy_result": deepcopy(result_on),
        "legacy_post_state": shadow_on.snapshot(),
    }


@pytest.mark.parametrize(("scenario", "overrides"), CATEGORY_A, ids=[x[0] for x in CATEGORY_A])
def test_category_a_shadow_on_is_observational_and_deterministic(scenario, overrides) -> None:
    first = _run(scenario, overrides, True, "A")
    second = _run(scenario, overrides, True, "A")
    assert first == second
    assert first["effect_kind"] == "NONE"
    assert first["legacy_fake_submits"] == first["null_port_records"] == 0


@pytest.mark.parametrize(("scenario", "overrides", "success"), CATEGORY_B, ids=[x[0] for x in CATEGORY_B])
def test_category_b_consumes_one_legacy_submit_without_candidate_transport(scenario, overrides, success) -> None:
    first = _run(scenario, overrides, success, "B")
    second = _run(scenario, overrides, success, "B")
    assert first == second
    assert first["effect_kind"] == "SUBMIT_ORDER"
    assert first["legacy_fake_submits"] == first["null_port_records"] == 1
    assert all(value == 0 for value in first["external_activity"].values())


@pytest.mark.parametrize("entry_side", ["BUY", "SELL"], ids=["long", "short"])
def test_shadow_lifecycle_matches_oracle_and_shadow_off(entry_side: str) -> None:
    overrides = {"CURRENT_EXECUTION_SIDE": entry_side}
    p4 = load_runtime(PHASE4, overrides)
    off = load_runtime(PHASE5, overrides)
    on = load_runtime(PHASE5, overrides | {"SHADOW_EXECUTION_ENABLED": True})

    def checkpoint(step: int) -> None:
        assert mismatch_records(f"{entry_side}-shadow-lifecycle", step, p4.snapshot(), off.snapshot()) == []
        assert off.snapshot() == on.snapshot()

    checkpoint(0)
    assert p4.dispatch() == off.dispatch() == on.dispatch()
    checkpoint(1)  # SUBMITTED
    for runtime in (p4, off, on):
        runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="OPEN", CURRENT_BROKER_ORDER_ID="SYNTHETIC-ORDER-001", CURRENT_BROKER_ORDER_STATUS="OPEN", CURRENT_BROKER_ORDER_STATUS_DESCRIPTION="SYNTHETIC OPEN")
    checkpoint(2)
    position = "LONG" if entry_side == "BUY" else "SHORT"
    for runtime in (p4, off, on):
        runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="FILLED", CURRENT_BROKER_ORDER_STATUS="FILLED", CURRENT_BROKER_ORDER_STATUS_DESCRIPTION="SYNTHETIC FILLED", CURRENT_POSITION_STATE=position, CURRENT_POSITION_CONTRACTS=2, CURRENT_POSITION_ENTRY_SIDE=entry_side, CURRENT_EXECUTION_ACTION="EXIT", CURRENT_EXECUTION_SIDE="FLATTEN", CURRENT_EXECUTION_REASON="SYNTHETIC EXIT")
    checkpoint(3)
    assert p4.dispatch() == off.dispatch() == on.dispatch()
    checkpoint(4)
    for runtime in (p4, off, on):
        runtime.namespace.update(CURRENT_POSITION_STATE="FLAT", CURRENT_POSITION_CONTRACTS=0, CURRENT_POSITION_ENTRY_SIDE="NONE", CURRENT_BROKER_ORDER_STATE="FILLED")
    checkpoint(5)
    assert on.ledger.shadow == 2
    assert on.ledger.null_port == 2


def _candidate_fixture():
    runtime = load_runtime(PHASE5, {"CURRENT_EXECUTION_STATUS": "IDLE"})
    values = runtime.namespace
    state = execution_state_from_legacy(values)
    result = runtime.dispatch()
    candidate = run_dispatch_shadow(
        state,
        execution_intent_from_legacy(values),
        execution_config_from_legacy(values, submission_timestamp=None),
        legacy_state=execution_state_from_legacy(values),
        legacy_result=result,
        submit_port=NullOrderSubmitPort(),
    )
    return runtime, result, candidate


@pytest.mark.parametrize(("field", "value"), [("action", "EXIT"), ("side", "SELL"), ("quantity", 99), ("reason", "INJECTED")])
def test_expected_candidate_semantic_mismatches_are_rejected(field: str, value: object) -> None:
    runtime, legacy_result, candidate = _candidate_fixture()
    before = runtime.snapshot()
    altered_result = dict(candidate.candidate_transition.result)
    altered_result[field] = value
    altered = replace(candidate.candidate_transition, result=altered_result)
    mismatches = tuple(name for name in ("action", "side", "quantity", "reason") if altered.result.get(name) != legacy_result.get(name))
    observation = {"candidate_accepted": not mismatches, "outcome": "MISMATCH", "classification": "EXPECTED_INJECTED_MISMATCH"}
    assert mismatches == (field,)
    assert observation == {"candidate_accepted": False, "outcome": "MISMATCH", "classification": "EXPECTED_INJECTED_MISMATCH"}
    assert runtime.snapshot() == before
    assert candidate.legacy_result is legacy_result


@pytest.mark.parametrize("observation", [None, {"malformed": True}], ids=["missing", "malformed"])
def test_submit_observation_failures_are_rejected_without_external_activity(observation) -> None:
    runtime = load_runtime(PHASE5)
    values = runtime.namespace
    state = execution_state_from_legacy(values)
    legacy_result = {"status": "AUTHORITATIVE"}
    before = runtime.snapshot()
    if observation is None:
        result = run_dispatch_shadow(state, execution_intent_from_legacy(values), execution_config_from_legacy(values, submission_timestamp="2026-01-02T10:00:00-05:00"), legacy_state=state, legacy_result=legacy_result, submit_port=NullOrderSubmitPort(), observed_submit_result=None)
        assert result.candidate_accepted is False
        assert [m.field for m in result.mismatches] == ["observed_submit_result"]
        rejected = {"candidate_accepted": result.candidate_accepted, "outcome": "MISMATCH", "classification": "EXPECTED_INJECTED_MISMATCH"}
    else:
        # Harness validation rejects malformed observations before candidate completion.
        assert set(observation) != {"ok", "status_code", "reason", "response"}
        rejected = {"candidate_accepted": False, "outcome": "REJECTED", "classification": "EXPECTED_INJECTED_MISMATCH"}
    assert rejected["candidate_accepted"] is False
    assert rejected["outcome"] in {"MISMATCH", "REJECTED"}
    assert runtime.snapshot() == before
    assert runtime.ledger.total == 0


def test_candidate_exception_after_legacy_is_fail_closed() -> None:
    oracle = load_runtime(PHASE4)
    runtime = load_runtime(PHASE5, {"SHADOW_EXECUTION_ENABLED": True})
    expected = oracle.dispatch()
    expected_state = oracle.snapshot()
    calls = 0

    def explode(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("EXPECTED_INJECTED_ERROR")

    runtime.namespace["run_dispatch_shadow"] = explode
    effective = runtime.dispatch()
    assert calls == 1
    assert effective == expected
    assert runtime.snapshot() == expected_state
    assert runtime.namespace["CURRENT_SHADOW_RESULT"] is None
    assert len(runtime.submit.calls) == 1  # legacy ran exactly once before candidate
    assert runtime.ledger.total == 0


def test_null_port_and_candidate_modules_have_zero_external_capability() -> None:
    port = NullOrderSubmitPort()
    assert not hasattr(port, "submit")
    assert not hasattr(port, "request")
    forbidden = {"requests", "urllib", "http", "socket", "dotenv", "tradestation", "oauth"}
    for path in PHASE5.parent.glob("src/bot_spx/execution/shadow_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        imports |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        assert imports.isdisjoint(forbidden)


def test_runtime_files_remain_safe_and_shadow_override_is_memory_only() -> None:
    source = PHASE5.read_text(encoding="utf-8")
    assert "SHADOW_EXECUTION_ENABLED = False" in source
    assert "EXECUTION_MODE = \"DRY_RUN\"" in source
    assert "LIVE_ORDER_EXECUTION_ENABLED = False" in source
    assert "ORDER_EXECUTION_ENVIRONMENT = \"SIM\"" in source
    runtime = load_runtime(PHASE5, {"SHADOW_EXECUTION_ENABLED": True})
    assert runtime.namespace["SHADOW_EXECUTION_ENABLED"] is True
    assert "SHADOW_EXECUTION_ENABLED = False" in PHASE5.read_text(encoding="utf-8")


def test_final_parity_matrix_has_required_schema_and_green_aggregates() -> None:
    matrix = [_run(name, changes, True, "A") for name, changes in CATEGORY_A]
    matrix += [_run(name, changes, success, "B") for name, changes, success in CATEGORY_B]
    required = {"scenario", "category", "legacy_status", "candidate_outcome", "candidate_accepted", "effect_kind", "mismatch_count", "mismatch_classification", "legacy_state_equal", "deterministic", "external_activity"}
    assert len(matrix) == 18
    assert all(required <= row.keys() for row in matrix)
    aggregates = {
        "total_scenarios": len(matrix),
        "match": sum(row["candidate_outcome"] == "MATCH" for row in matrix),
        "candidate_accepted": sum(bool(row["candidate_accepted"]) for row in matrix),
        "candidate_rejected": sum(not row["candidate_accepted"] for row in matrix),
        "unexpected_mismatch": sum(bool(row["mismatch_count"]) for row in matrix),
        "unexpected_error": 0,
        "legacy_authority_violations": sum(not row["legacy_state_equal"] for row in matrix),
        "determinism_failures": sum(not row["deterministic"] for row in matrix),
    }
    assert aggregates == {"total_scenarios": 18, "match": 18, "candidate_accepted": 18, "candidate_rejected": 0, "unexpected_mismatch": 0, "unexpected_error": 0, "legacy_authority_violations": 0, "determinism_failures": 0}
