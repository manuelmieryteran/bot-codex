"""Execution safety checks preserved from Phase 4."""

from bot_spx.execution.position_validation import validate_position_state


def execution_safety_check(
    execution_mode,
    live_order_execution_enabled,
    position_reconciliation_ok,
    execution_status,
    execution_action,
    execution_side,
    execution_quantity,
    position_state,
    position_contracts,
    position_entry_side,
):
    if execution_mode != "LIVE":
        return False, "EXECUTION MODE IS NOT LIVE"

    if not live_order_execution_enabled:
        return False, "LIVE ORDER EXECUTION DISABLED"

    if not position_reconciliation_ok:
        return False, "POSITION RECONCILIATION NOT OK"

    if execution_status != "READY":
        return False, "EXECUTION STATUS NOT READY"

    position_valid, position_reason = validate_position_state(
        position_state,
        position_contracts,
        position_entry_side,
    )

    if not position_valid:
        return False, position_reason

    if execution_action not in ("ENTRY", "EXIT"):
        return False, "INVALID EXECUTION ACTION"

    if execution_action == "ENTRY":
        if execution_side not in ("BUY", "SELL"):
            return False, "INVALID ENTRY SIDE"

        if execution_quantity <= 0:
            return False, "INVALID ENTRY QUANTITY"

    if execution_action == "EXIT":
        if execution_side != "FLATTEN":
            return False, "INVALID EXIT SIDE"

    return True, "EXECUTION SAFETY CHECK PASSED"
