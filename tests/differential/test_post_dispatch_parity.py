"""Differential parity for the AST-isolated post-dispatch legacy block."""

from __future__ import annotations

import ast
from dataclasses import asdict
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.dispatch_models import ExecutionState
from bot_spx.execution.post_dispatch import post_dispatch_transition
from tests.characterization.legacy_harness import (
    FixedUUIDValue,
    load_post_dispatch_transition,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "post_dispatch.py"
)
INITIAL_STATE = ExecutionState(
    broker_account_id=None,
    broker_position_available=False,
    broker_position_reason="SENTINEL_BROKER_POSITION_REASON",
    position_reconciliation_ok=False,
    position_reconciliation_action="BLOCK",
    position_reconciliation_reason="SENTINEL_RECONCILIATION_REASON",
    broker_order_state="SENTINEL_BROKER_STATE",
    broker_order_id="SENTINEL_BROKER_ID",
    broker_order_status="SENTINEL_BROKER_STATUS",
    broker_order_status_description="SENTINEL_BROKER_DESCRIPTION",
    dispatch_status="SENTINEL_DISPATCH_STATUS",
    dispatch_reason="SENTINEL_DISPATCH_REASON",
    dispatch_id="SENTINEL_DISPATCH_ID",
    position_state="LONG",
    position_contracts=3,
    position_entry_side="BUY",
    last_dispatch_signature=("ENTRY", "BUY", 2, "LONG MEAN REVERSION"),
    pending_order_action="ENTRY",
    pending_order_side="BUY",
    pending_order_quantity=2,
    pending_order_symbol="SYNTHETIC-ES",
    pending_order_submitted_at="2026-01-01T10:00:00-05:00",
)


@pytest.mark.parametrize(
    ("case", "dispatch_result", "expected_uuid_calls"),
    [
        (
            "submitted-orders-order-id",
            {
                "status": "SUBMITTED",
                "reason": "SYNTHETIC SUBMIT SUCCESS",
                "broker_response": {
                    "Orders": [
                        {
                            "OrderID": "SYNTHETIC-ORDER-ID-001",
                            "Status": "RECEIVED",
                        }
                    ]
                },
            },
            1,
        ),
        (
            "submitted-top-level-order-id",
            {
                "status": "SUBMITTED",
                "reason": "SYNTHETIC SUBMIT SUCCESS",
                "broker_response": {
                    "OrderID": "SYNTHETIC-TOP-LEVEL-ID",
                    "OrderStatus": "QUEUED",
                },
            },
            1,
        ),
        (
            "submitted-without-order-id",
            {
                "status": "SUBMITTED",
                "reason": "SYNTHETIC SUBMIT SUCCESS",
                "broker_response": {"Orders": [{}]},
            },
            1,
        ),
        (
            "ordinary-submit-failed-preserves-broker-state",
            {
                "status": "SUBMIT_FAILED",
                "reason": "SYNTHETIC SUBMIT FAILURE",
                "broker_response": {"synthetic": True},
            },
            1,
        ),
        (
            "unknown-submit-status",
            {
                "status": "SUBMIT_FAILED",
                "reason": "ORDER SUBMISSION STATUS UNKNOWN: SYNTHETIC TIMEOUT",
                "broker_response": None,
            },
            1,
        ),
        (
            "idle-clears-dispatch-id",
            {"status": "IDLE", "reason": "NO EXECUTION REQUEST"},
            0,
        ),
        (
            "missing-status-and-reason-use-fallbacks",
            {},
            1,
        ),
    ],
)
def test_modular_post_dispatch_matches_ast_isolated_oracle(
    case: str,
    dispatch_result: dict[str, object],
    expected_uuid_calls: int,
) -> None:
    oracle = load_post_dispatch_transition(
        dispatch_result=dispatch_result,
        dispatch_status=INITIAL_STATE.dispatch_status,
        dispatch_reason=INITIAL_STATE.dispatch_reason,
        dispatch_id=INITIAL_STATE.dispatch_id,
        broker_order_id=INITIAL_STATE.broker_order_id,
        broker_order_status=INITIAL_STATE.broker_order_status,
        broker_order_state=INITIAL_STATE.broker_order_state,
        broker_order_status_description=(
            INITIAL_STATE.broker_order_status_description
        ),
    )

    oracle.function()
    candidate = post_dispatch_transition(
        INITIAL_STATE,
        dispatch_result,
        FixedUUIDValue.hex,
    )
    candidate_values = asdict(candidate)

    assert candidate_values["dispatch_status"] == oracle.namespace[
        "CURRENT_DISPATCH_STATUS"
    ], case
    assert candidate_values["dispatch_reason"] == oracle.namespace[
        "CURRENT_DISPATCH_REASON"
    ], case
    assert candidate_values["dispatch_id"] == oracle.namespace[
        "CURRENT_DISPATCH_ID"
    ], case
    assert candidate_values["broker_order_id"] == oracle.namespace[
        "CURRENT_BROKER_ORDER_ID"
    ], case
    assert candidate_values["broker_order_status"] == oracle.namespace[
        "CURRENT_BROKER_ORDER_STATUS"
    ], case
    assert candidate_values["broker_order_state"] == oracle.namespace[
        "CURRENT_BROKER_ORDER_STATE"
    ], case
    assert candidate_values["broker_order_status_description"] == oracle.namespace[
        "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION"
    ], case
    assert candidate.position_state == INITIAL_STATE.position_state
    assert candidate.position_contracts == INITIAL_STATE.position_contracts
    assert candidate.position_entry_side == INITIAL_STATE.position_entry_side
    assert candidate.pending_order_action == INITIAL_STATE.pending_order_action
    assert candidate.pending_order_side == INITIAL_STATE.pending_order_side
    assert candidate.pending_order_quantity == INITIAL_STATE.pending_order_quantity
    assert candidate.pending_order_symbol == INITIAL_STATE.pending_order_symbol
    assert (
        candidate.pending_order_submitted_at
        == INITIAL_STATE.pending_order_submitted_at
    )
    assert oracle.uuid.call_count == expected_uuid_calls
    assert "display_snapshot" not in oracle.namespace
    assert "requests" not in oracle.namespace
    assert "tradestation_request" not in oracle.namespace


def test_post_dispatch_transition_public_signature_is_explicit() -> None:
    signature = inspect.signature(post_dispatch_transition)

    assert list(signature.parameters) == ["state", "dispatch_result", "dispatch_id"]


def test_post_dispatch_candidate_has_no_external_capability() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    imported_modules = {
        node.module or ""
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }

    assert imported_modules == {
        "dataclasses",
        "bot_spx.execution.dispatch_models",
    }
    for forbidden_reference in (
        "requests",
        "http",
        "tradestation_request",
        "submit_tradestation_order",
        "token",
        "credential",
        "dotenv",
        "uuid",
    ):
        assert forbidden_reference not in source.lower()
