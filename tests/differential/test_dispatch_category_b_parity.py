"""Differential parity for pure category-B dispatch effect transitions."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from bot_spx.execution.dispatch import complete_submit_effect, dispatch_transition
from bot_spx.execution.dispatch_models import (
    DispatchConfig,
    ExecutionIntent,
    ExecutionState,
)
from tests.characterization.legacy_harness import (
    FIXED_PENDING_TIMESTAMP,
    SYNTHETIC_SUBMIT_FAILURE,
    SYNTHETIC_SUBMIT_SUCCESS,
    load_dispatch_execution_category_b_failure,
    load_dispatch_execution_category_b_success,
)


EXPECTED_PAYLOAD = {
    "AccountID": "SYNTHETIC-ACCOUNT",
    "Symbol": "SYNTHETIC-ES",
    "Quantity": "2",
    "OrderType": "MARKET",
    "TradeAction": "BUY",
    "TimeInForce": {"Duration": "DAY"},
    "Route": "Intelligent",
}
INITIAL_STATE = ExecutionState(
    broker_account_id=None,
    broker_position_available=False,
    broker_position_reason="SENTINEL_BROKER_POSITION_REASON",
    position_reconciliation_ok=False,
    position_reconciliation_action="BLOCK",
    position_reconciliation_reason="SENTINEL_RECONCILIATION_REASON",
    broker_order_state="NONE",
    broker_order_id=None,
    broker_order_status="NONE",
    broker_order_status_description="NONE",
    dispatch_status="SENTINEL_DISPATCH_STATUS",
    dispatch_reason="SENTINEL_DISPATCH_REASON",
    dispatch_id="SENTINEL_DISPATCH_ID",
    position_state="FLAT",
    position_contracts=0,
    position_entry_side="NONE",
    last_dispatch_signature=("PREVIOUS", "NONE", 99, "PREVIOUS REASON"),
    pending_order_action="SENTINEL_ACTION",
    pending_order_side="SENTINEL_SIDE",
    pending_order_quantity=91,
    pending_order_symbol="SENTINEL_SYMBOL",
    pending_order_submitted_at="SENTINEL_TIME",
)
INTENT = ExecutionIntent(
    status="READY",
    action="ENTRY",
    side="BUY",
    quantity=2,
    symbol="SYNTHETIC-ES",
    order_type="MARKET",
    reason="LONG MEAN REVERSION",
)
CONFIG = DispatchConfig(
    execution_mode="LIVE",
    live_order_execution_enabled=True,
    position_reconciliation_ok=True,
    broker_account_id="SYNTHETIC-ACCOUNT",
    submission_timestamp=FIXED_PENDING_TIMESTAMP,
)


def _oracle_state(namespace: dict[str, object]) -> dict[str, object]:
    return {
        "broker_account_id": INITIAL_STATE.broker_account_id,
        "broker_position_available": INITIAL_STATE.broker_position_available,
        "broker_position_reason": INITIAL_STATE.broker_position_reason,
        "position_reconciliation_ok": INITIAL_STATE.position_reconciliation_ok,
        "position_reconciliation_action": INITIAL_STATE.position_reconciliation_action,
        "position_reconciliation_reason": INITIAL_STATE.position_reconciliation_reason,
        "broker_order_state": namespace["CURRENT_BROKER_ORDER_STATE"],
        "broker_order_id": INITIAL_STATE.broker_order_id,
        "broker_order_status": INITIAL_STATE.broker_order_status,
        "broker_order_status_description": INITIAL_STATE.broker_order_status_description,
        "dispatch_status": INITIAL_STATE.dispatch_status,
        "dispatch_reason": INITIAL_STATE.dispatch_reason,
        "dispatch_id": INITIAL_STATE.dispatch_id,
        "position_state": namespace["CURRENT_POSITION_STATE"],
        "position_contracts": namespace["CURRENT_POSITION_CONTRACTS"],
        "position_entry_side": namespace["CURRENT_POSITION_ENTRY_SIDE"],
        "last_dispatch_signature": namespace["LAST_DISPATCH_SIGNATURE"],
        "pending_order_action": namespace["CURRENT_PENDING_ORDER_ACTION"],
        "pending_order_side": namespace["CURRENT_PENDING_ORDER_SIDE"],
        "pending_order_quantity": namespace["CURRENT_PENDING_ORDER_QUANTITY"],
        "pending_order_symbol": namespace["CURRENT_PENDING_ORDER_SYMBOL"],
        "pending_order_submitted_at": namespace[
            "CURRENT_PENDING_ORDER_SUBMITTED_AT"
        ],
    }


@pytest.mark.parametrize(
    ("oracle_loader", "submit_result"),
    [
        (load_dispatch_execution_category_b_failure, SYNTHETIC_SUBMIT_FAILURE),
        (load_dispatch_execution_category_b_success, SYNTHETIC_SUBMIT_SUCCESS),
    ],
    ids=["submit-failure", "submit-success"],
)
def test_modular_category_b_effect_chain_matches_phase4_oracle(
    oracle_loader,
    submit_result: dict[str, object],
) -> None:
    oracle = oracle_loader()
    oracle_result = oracle.function()

    prepared = dispatch_transition(INITIAL_STATE, INTENT, CONFIG)

    assert prepared.effect.kind == "SUBMIT_ORDER"
    assert prepared.effect.payload == EXPECTED_PAYLOAD
    assert prepared.result == {}
    completed = complete_submit_effect(
        prepared.state,
        INTENT,
        "EXECUTION SAFETY CHECK PASSED",
        submit_result,
    )

    assert completed.result == oracle_result
    assert asdict(completed.state) == _oracle_state(oracle.namespace)
    assert completed.effect.kind == "NONE"
    assert completed.effect.payload is None
    assert completed.state.position_state == "FLAT"
    assert completed.state.position_contracts == 0
    assert completed.state.position_entry_side == "NONE"
    assert oracle.submit.call_count == 1
    assert oracle.submit.payloads == [prepared.effect.payload]
    assert oracle.clock.call_count == 1
    assert oracle.transport.call_count == 0


def test_failed_submit_preserves_consumed_signature_and_blocks_identical_retry() -> None:
    prepared = dispatch_transition(INITIAL_STATE, INTENT, CONFIG)
    completed = complete_submit_effect(
        prepared.state,
        INTENT,
        "EXECUTION SAFETY CHECK PASSED",
        SYNTHETIC_SUBMIT_FAILURE,
    )

    retry = dispatch_transition(completed.state, INTENT, CONFIG)

    assert completed.state.last_dispatch_signature == (
        "ENTRY",
        "BUY",
        2,
        "LONG MEAN REVERSION",
    )
    assert retry.result["status"] == "DUPLICATE_BLOCKED"
    assert retry.state == completed.state
    assert retry.effect.kind == "NONE"
