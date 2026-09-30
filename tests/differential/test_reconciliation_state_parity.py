"""Differential parity for pure reconciliation-state updates."""

from __future__ import annotations

import inspect
from dataclasses import asdict

import pytest

from bot_spx.execution.dispatch_models import ExecutionState
from bot_spx.execution.position_reconciliation import (
    update_broker_reconciliation_state,
)
from tests.characterization.legacy_harness import (
    load_update_broker_reconciliation_state,
)


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
    ("case", "account_id", "lookup_result"),
    [
        (
            "lookup-failure-with-reason",
            "SYNTHETIC-ACCOUNT",
            {"ok": False, "reason": "SYNTHETIC LOOKUP FAILURE"},
        ),
        ("lookup-failure-default-reason", None, {"ok": False}),
        (
            "available-flat-match",
            "SYNTHETIC-ACCOUNT",
            {"ok": True, "reason": "SYNTHETIC AVAILABLE", "position": None},
        ),
        (
            "available-mismatch",
            "SYNTHETIC-ACCOUNT",
            {"ok": True, "position": {"Quantity": 2}},
        ),
        (
            "available-unknown",
            "SYNTHETIC-ACCOUNT",
            {"ok": True, "position": {"Quantity": "ABC"}},
        ),
    ],
)
def test_modular_reconciliation_state_update_matches_phase4_oracle(
    case: str,
    account_id: str | None,
    lookup_result: dict[str, object],
) -> None:
    oracle = load_update_broker_reconciliation_state(
        position_state=INITIAL_STATE.position_state,
        position_contracts=INITIAL_STATE.position_contracts,
        position_entry_side=INITIAL_STATE.position_entry_side,
        broker_account_id=INITIAL_STATE.broker_account_id,
        broker_position_available=INITIAL_STATE.broker_position_available,
        broker_position_reason=INITIAL_STATE.broker_position_reason,
        reconciliation_ok=INITIAL_STATE.position_reconciliation_ok,
        reconciliation_action=INITIAL_STATE.position_reconciliation_action,
        reconciliation_reason=INITIAL_STATE.position_reconciliation_reason,
    )

    assert oracle.function(account_id, lookup_result) is None
    candidate = update_broker_reconciliation_state(
        INITIAL_STATE,
        account_id,
        lookup_result,
    )
    candidate_values = asdict(candidate)

    for candidate_name, oracle_name in RECONCILIATION_FIELDS.items():
        assert candidate_values[candidate_name] == oracle.namespace[oracle_name], case
    for name, value in asdict(INITIAL_STATE).items():
        if name not in RECONCILIATION_FIELDS:
            assert candidate_values[name] == value, case
    assert oracle.transport.call_count == 0


def test_reconciliation_state_update_public_signature_is_explicit() -> None:
    signature = inspect.signature(update_broker_reconciliation_state)

    assert list(signature.parameters) == [
        "state",
        "account_id",
        "broker_lookup_result",
    ]
