"""Pure internal-versus-broker reconciliation preserved from Phase 4."""

from dataclasses import replace

from bot_spx.execution.position_comparison import (
    compare_internal_vs_broker_position,
)


def reconcile_internal_with_broker_position(
    position_state,
    position_contracts,
    position_entry_side,
    broker_position,
):
    comparison = compare_internal_vs_broker_position(
        position_state,
        position_contracts,
        position_entry_side,
        broker_position,
    )

    if comparison["match"]:
        return {
            "ok": True,
            "action": "NONE",
            "reason": comparison["reason"],
        }

    if comparison["broker_state"] == "UNKNOWN":
        return {
            "ok": False,
            "action": "BLOCK",
            "reason": "BROKER POSITION UNKNOWN",
        }

    return {
        "ok": False,
        "action": "BLOCK",
        "reason": "POSITION RECONCILIATION REQUIRED",
    }


def update_broker_reconciliation_state(state, account_id, broker_lookup_result):
    if not broker_lookup_result.get("ok"):
        return replace(
            state,
            broker_account_id=account_id,
            broker_position_available=False,
            broker_position_reason=broker_lookup_result.get(
                "reason",
                "BROKER POSITION LOOKUP FAILED",
            ),
            position_reconciliation_ok=False,
            position_reconciliation_action="BLOCK",
            position_reconciliation_reason="BROKER POSITION UNAVAILABLE",
        )

    reconciliation = reconcile_internal_with_broker_position(
        state.position_state,
        state.position_contracts,
        state.position_entry_side,
        broker_lookup_result.get("position"),
    )
    return replace(
        state,
        broker_account_id=account_id,
        broker_position_available=True,
        broker_position_reason=broker_lookup_result.get(
            "reason",
            "BROKER POSITION AVAILABLE",
        ),
        position_reconciliation_ok=reconciliation.get("ok", False),
        position_reconciliation_action=reconciliation.get("action", "BLOCK"),
        position_reconciliation_reason=reconciliation.get(
            "reason",
            "RECONCILIATION FAILED",
        ),
    )
