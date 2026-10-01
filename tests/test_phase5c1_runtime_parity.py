"""Controlled end-to-end legacy runtime parity with Phase 5 shadow disabled."""

from __future__ import annotations

import ast
import difflib

import pytest

from tests.runtime_parity_harness import FIXED_TIME, PHASE4, PHASE5, mismatch_records, paired


SCENARIOS = [
    ("idle", {"CURRENT_EXECUTION_STATUS": "IDLE"}, True),
    ("broker-open", {"CURRENT_BROKER_ORDER_STATE": "OPEN"}, True),
    ("broker-unknown", {"CURRENT_BROKER_ORDER_STATE": "UNKNOWN"}, True),
    ("entry-while-long", {"CURRENT_POSITION_STATE": "LONG", "CURRENT_POSITION_CONTRACTS": 1, "CURRENT_POSITION_ENTRY_SIDE": "BUY"}, True),
    ("exit-while-flat", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN"}, True),
    ("duplicate", {"LAST_DISPATCH_SIGNATURE": ("ENTRY", "BUY", 2, "SYNTHETIC INTENT")}, True),
    ("dry-run-buy", {"EXECUTION_MODE": "DRY_RUN"}, True),
    ("dry-run-sell", {"EXECUTION_MODE": "DRY_RUN", "CURRENT_EXECUTION_SIDE": "SELL"}, True),
    ("safety-live-disabled", {"LIVE_ORDER_EXECUTION_ENABLED": False}, True),
    ("safety-reconciliation", {"CURRENT_POSITION_RECONCILIATION_OK": False}, True),
    ("payload-account", {"CURRENT_BROKER_ACCOUNT_ID": None}, True),
    ("payload-symbol", {"CURRENT_EXECUTION_SYMBOL": ""}, True),
    ("entry-buy-success", {}, True),
    ("entry-buy-failure", {}, False),
    ("entry-sell-success", {"CURRENT_EXECUTION_SIDE": "SELL"}, True),
    ("entry-sell-failure", {"CURRENT_EXECUTION_SIDE": "SELL"}, False),
    ("exit-long-success", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "LONG", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "BUY"}, True),
    ("exit-long-failure", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "LONG", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "BUY"}, False),
    ("exit-short-success", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "SHORT", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "SELL"}, True),
    ("exit-short-failure", {"CURRENT_EXECUTION_ACTION": "EXIT", "CURRENT_EXECUTION_SIDE": "FLATTEN", "CURRENT_POSITION_STATE": "SHORT", "CURRENT_POSITION_CONTRACTS": 2, "CURRENT_POSITION_ENTRY_SIDE": "SELL"}, False),
]


@pytest.mark.parametrize(("scenario", "overrides", "success"), SCENARIOS, ids=[x[0] for x in SCENARIOS])
def test_controlled_dispatch_parity(scenario: str, overrides: dict[str, object], success: bool) -> None:
    phase4, phase5 = paired(overrides, submit_success=success)
    pre4, pre5 = phase4.snapshot(), phase5.snapshot()
    result4, result5 = phase4.dispatch(), phase5.dispatch()
    post4, post5 = phase4.snapshot(), phase5.snapshot()

    mismatches = (
        mismatch_records(scenario, 0, pre4, pre5)
        + mismatch_records(scenario, 1, result4, result5)
        + mismatch_records(scenario, 1, post4, post5)
        + mismatch_records(scenario, 1, phase4.submit.calls, phase5.submit.calls)
    )
    assert mismatches == []
    assert phase4.ledger.total == phase5.ledger.total == 0
    assert phase5.ledger.shadow == phase5.ledger.null_port == 0
    assert len(phase4.submit.calls) == len(phase5.submit.calls)
    if phase4.submit.calls:
        assert post4["CURRENT_PENDING_ORDER_SUBMITTED_AT"] == FIXED_TIME


@pytest.mark.parametrize("entry_side", ["BUY", "SELL"], ids=["long-lifecycle", "short-lifecycle"])
def test_deterministic_multistep_lifecycle(entry_side: str) -> None:
    """Replay FLAT→ENTRY→SUBMITTED→OPEN→FILLED→position→EXIT→FILLED→FLAT."""
    p4, p5 = paired({"CURRENT_EXECUTION_SIDE": entry_side})
    comparisons = 0

    def compare(step: int) -> None:
        nonlocal comparisons
        assert mismatch_records(f"{entry_side}-lifecycle", step, p4.snapshot(), p5.snapshot()) == []
        comparisons += 1

    compare(0)
    assert p4.dispatch() == p5.dispatch()  # submitted
    compare(1)
    for runtime in (p4, p5):
        runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="OPEN", CURRENT_BROKER_ORDER_ID="SYNTHETIC-ORDER-001", CURRENT_BROKER_ORDER_STATUS="OPEN", CURRENT_BROKER_ORDER_STATUS_DESCRIPTION="SYNTHETIC OPEN")
    compare(2)
    position = "LONG" if entry_side == "BUY" else "SHORT"
    for runtime in (p4, p5):
        runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="FILLED", CURRENT_BROKER_ORDER_STATUS="FILLED", CURRENT_BROKER_ORDER_STATUS_DESCRIPTION="SYNTHETIC FILLED", CURRENT_POSITION_STATE=position, CURRENT_POSITION_CONTRACTS=2, CURRENT_POSITION_ENTRY_SIDE=entry_side, CURRENT_EXECUTION_ACTION="EXIT", CURRENT_EXECUTION_SIDE="FLATTEN", CURRENT_EXECUTION_REASON="SYNTHETIC EXIT")
    compare(3)
    assert p4.dispatch() == p5.dispatch()
    compare(4)
    for runtime in (p4, p5):
        runtime.namespace.update(CURRENT_POSITION_STATE="FLAT", CURRENT_POSITION_CONTRACTS=0, CURRENT_POSITION_ENTRY_SIDE="NONE", CURRENT_BROKER_ORDER_STATE="FILLED")
    compare(5)
    assert comparisons == 6
    assert p4.ledger.total == p5.ledger.total == 0


def test_mismatch_report_schema_and_classification() -> None:
    records = mismatch_records("synthetic", 7, {"field": "oracle"}, {"field": "candidate"})
    assert records == [{"scenario": "synthetic", "step": 7, "field": "field", "phase4": "oracle", "phase5": "candidate", "expected": "oracle", "actual": "candidate", "classification": "LEGACY_PARITY_REGRESSION"}]


def test_scenarios_are_isolated() -> None:
    first4, first5 = paired()
    first4.namespace["CURRENT_POSITION_STATE"] = "MUTATED"
    first5.namespace["CURRENT_POSITION_STATE"] = "MUTATED"
    second4, second5 = paired()
    assert second4.namespace["CURRENT_POSITION_STATE"] == "FLAT"
    assert second5.namespace["CURRENT_POSITION_STATE"] == "FLAT"
    assert first4.namespace is not second4.namespace
    assert first5.namespace is not second5.namespace


def test_ast_audit_freezes_exact_legacy_dispatch_differences() -> None:
    """Phase 5 legacy differs only by its name and submit observation hook."""
    def source(path, name):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        return ast.unparse(function).replace("_dispatch_execution_legacy", "dispatch_execution", 1).splitlines()

    delta = list(difflib.unified_diff(source(PHASE4, "dispatch_execution"), source(PHASE5, "_dispatch_execution_legacy"), n=0))
    additions = [line[1:].strip() for line in delta if line.startswith("+") and not line.startswith("+++")]
    removals = [line for line in delta if line.startswith("-") and not line.startswith("---")]
    assert removals == []
    assert additions == [
        "global _LAST_LEGACY_SUBMIT_OBSERVATION",
        "_LAST_LEGACY_SUBMIT_OBSERVATION = submit_result",
    ]
