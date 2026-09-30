"""Differential parity for category-A modular dispatch transitions."""

from __future__ import annotations

import ast
from dataclasses import asdict
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.dispatch import dispatch_transition
from bot_spx.execution.dispatch_models import (
    DispatchConfig,
    ExecutionIntent,
    ExecutionState,
)
from tests.characterization.legacy_harness import load_dispatch_execution_category_a


DISPATCH_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "dispatch.py"
)
INITIAL_SIGNATURE = ("PREVIOUS", "NONE", 99, "PREVIOUS REASON")
INITIAL_STATE = {
    "broker_account_id": None,
    "broker_position_available": False,
    "broker_position_reason": "SENTINEL_BROKER_POSITION_REASON",
    "position_reconciliation_ok": False,
    "position_reconciliation_action": "BLOCK",
    "position_reconciliation_reason": "SENTINEL_RECONCILIATION_REASON",
    "broker_order_state": "NONE",
    "broker_order_id": None,
    "broker_order_status": "NONE",
    "broker_order_status_description": "NONE",
    "dispatch_status": "SENTINEL_DISPATCH_STATUS",
    "dispatch_reason": "SENTINEL_DISPATCH_REASON",
    "dispatch_id": "SENTINEL_DISPATCH_ID",
    "position_state": "FLAT",
    "position_contracts": 0,
    "position_entry_side": "NONE",
    "last_dispatch_signature": INITIAL_SIGNATURE,
    "pending_order_action": "SENTINEL_ACTION",
    "pending_order_side": "SENTINEL_SIDE",
    "pending_order_quantity": 91,
    "pending_order_symbol": "SENTINEL_SYMBOL",
    "pending_order_submitted_at": "SENTINEL_TIME",
}
INITIAL_INTENT = {
    "status": "READY",
    "action": "ENTRY",
    "side": "BUY",
    "quantity": 2,
    "symbol": "SYNTHETIC-ES",
    "order_type": "MARKET",
    "reason": "LONG MEAN REVERSION",
}
INITIAL_CONFIG = {
    "execution_mode": "LIVE",
    "live_order_execution_enabled": True,
    "position_reconciliation_ok": True,
    "broker_account_id": "SYNTHETIC-ACCOUNT",
    "submission_timestamp": None,
}


@pytest.mark.parametrize(
    ("case", "state_changes", "intent_changes", "config_changes"),
    [
        ("idle", {}, {"status": "IDLE"}, {}),
        ("broker-open", {"broker_order_state": "OPEN"}, {}, {}),
        ("broker-unknown", {"broker_order_state": "UNKNOWN"}, {}, {}),
        (
            "entry-position-long",
            {
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
            {},
            {},
        ),
        (
            "exit-position-flat",
            {},
            {
                "action": "EXIT",
                "side": "FLATTEN",
                "quantity": 0,
                "reason": "FORCED EXIT",
            },
            {},
        ),
        (
            "duplicate",
            {
                "last_dispatch_signature": (
                    "ENTRY",
                    "BUY",
                    2,
                    "LONG MEAN REVERSION",
                )
            },
            {},
            {},
        ),
        (
            "dry-run-entry-buy",
            {},
            {},
            {"execution_mode": "DRY_RUN", "live_order_execution_enabled": False},
        ),
        (
            "dry-run-entry-sell",
            {},
            {"side": "SELL", "reason": "SHORT BREAKDOWN"},
            {"execution_mode": "DRY_RUN", "live_order_execution_enabled": False},
        ),
        (
            "dry-run-exit-long",
            {
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
            {
                "action": "EXIT",
                "side": "FLATTEN",
                "quantity": 0,
                "reason": "FORCED EXIT",
            },
            {"execution_mode": "DRY_RUN", "live_order_execution_enabled": False},
        ),
        (
            "dry-run-exit-short",
            {
                "position_state": "SHORT",
                "position_contracts": 3,
                "position_entry_side": "SELL",
            },
            {
                "action": "EXIT",
                "side": "FLATTEN",
                "quantity": 0,
                "reason": "FORCED EXIT",
            },
            {"execution_mode": "DRY_RUN", "live_order_execution_enabled": False},
        ),
        (
            "safety-false-live",
            {},
            {},
            {"position_reconciliation_ok": False},
        ),
        (
            "payload-invalid-account",
            {},
            {},
            {"broker_account_id": None},
        ),
    ],
)
def test_modular_category_a_dispatch_matches_phase4_oracle(
    case: str,
    state_changes: dict[str, object],
    intent_changes: dict[str, object],
    config_changes: dict[str, object],
) -> None:
    state_values = INITIAL_STATE | state_changes
    intent_values = INITIAL_INTENT | intent_changes
    config_values = INITIAL_CONFIG | config_changes
    state = ExecutionState(**state_values)
    intent = ExecutionIntent(**intent_values)
    config = DispatchConfig(**config_values)
    oracle = load_dispatch_execution_category_a(
        execution_status=intent.status,
        execution_action=intent.action,
        execution_side=intent.side,
        execution_quantity=intent.quantity,
        execution_symbol=intent.symbol,
        execution_order_type=intent.order_type,
        execution_reason=intent.reason,
        broker_order_state=state.broker_order_state,
        position_state=state.position_state,
        position_contracts=state.position_contracts,
        position_entry_side=state.position_entry_side,
        execution_mode=config.execution_mode,
        live_order_execution_enabled=config.live_order_execution_enabled,
        position_reconciliation_ok=config.position_reconciliation_ok,
        last_dispatch_signature=state.last_dispatch_signature,
        pending_order_action=state.pending_order_action,
        pending_order_side=state.pending_order_side,
        pending_order_quantity=state.pending_order_quantity,
        pending_order_symbol=state.pending_order_symbol,
        pending_order_submitted_at=state.pending_order_submitted_at,
        broker_account_id=config.broker_account_id,
    )

    oracle_result = oracle.function()
    transition = dispatch_transition(state, intent, config)
    oracle_state = {
        "broker_account_id": state.broker_account_id,
        "broker_position_available": state.broker_position_available,
        "broker_position_reason": state.broker_position_reason,
        "position_reconciliation_ok": state.position_reconciliation_ok,
        "position_reconciliation_action": state.position_reconciliation_action,
        "position_reconciliation_reason": state.position_reconciliation_reason,
        "broker_order_state": oracle.namespace["CURRENT_BROKER_ORDER_STATE"],
        "broker_order_id": state.broker_order_id,
        "broker_order_status": state.broker_order_status,
        "broker_order_status_description": state.broker_order_status_description,
        "dispatch_status": state.dispatch_status,
        "dispatch_reason": state.dispatch_reason,
        "dispatch_id": state.dispatch_id,
        "position_state": oracle.namespace["CURRENT_POSITION_STATE"],
        "position_contracts": oracle.namespace["CURRENT_POSITION_CONTRACTS"],
        "position_entry_side": oracle.namespace["CURRENT_POSITION_ENTRY_SIDE"],
        "last_dispatch_signature": oracle.namespace["LAST_DISPATCH_SIGNATURE"],
        "pending_order_action": oracle.namespace["CURRENT_PENDING_ORDER_ACTION"],
        "pending_order_side": oracle.namespace["CURRENT_PENDING_ORDER_SIDE"],
        "pending_order_quantity": oracle.namespace["CURRENT_PENDING_ORDER_QUANTITY"],
        "pending_order_symbol": oracle.namespace["CURRENT_PENDING_ORDER_SYMBOL"],
        "pending_order_submitted_at": oracle.namespace[
            "CURRENT_PENDING_ORDER_SUBMITTED_AT"
        ],
    }

    assert transition.result == oracle_result, case
    assert asdict(transition.state) == oracle_state, case
    assert transition.effect.kind == "NONE"
    assert transition.effect.payload is None
    assert state == ExecutionState(**state_values)
    assert oracle.submit.call_count == 0
    assert oracle.transport.call_count == 0
    assert oracle.clock.call_count == 0


def test_valid_live_path_requires_explicit_timestamp() -> None:
    with pytest.raises(ValueError, match="^SUBMISSION TIMESTAMP REQUIRED$"):
        dispatch_transition(
            ExecutionState(**INITIAL_STATE),
            ExecutionIntent(**INITIAL_INTENT),
            DispatchConfig(**INITIAL_CONFIG),
        )


def test_dispatch_transition_public_signature_is_explicit() -> None:
    signature = inspect.signature(dispatch_transition)

    assert list(signature.parameters) == ["state", "intent", "config"]


def test_dispatch_core_has_no_external_capability() -> None:
    source = DISPATCH_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(DISPATCH_PATH))
    imported_modules = {
        node.module or ""
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }

    assert imported_modules == {
        "dataclasses",
        "bot_spx.execution.dispatch_models",
        "bot_spx.execution.execution_safety",
        "bot_spx.execution.order_payload",
        "bot_spx.execution.payload_validation",
    }
    for forbidden_reference in (
        "requests",
        "http",
        "tradestation_request",
        "submit_tradestation_order",
        "token",
        "credential",
        "dotenv",
    ):
        assert forbidden_reference not in source.lower()


def test_operational_baseline_does_not_import_modular_dispatch() -> None:
    baseline_path = DISPATCH_PATH.parents[3] / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
    tree = ast.parse(baseline_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert "bot_spx.execution.dispatch" not in imported_modules
