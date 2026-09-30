"""Explicit bridge from legacy execution globals to modular dispatch inputs."""

from collections.abc import Mapping
from typing import Any

from bot_spx.execution.dispatch_models import (
    DispatchConfig,
    ExecutionIntent,
    ExecutionState,
)


def execution_state_from_legacy(values: Mapping[str, Any]) -> ExecutionState:
    """Snapshot only the legacy globals consumed by the modular dispatcher."""
    return ExecutionState(
        broker_account_id=values["CURRENT_BROKER_ACCOUNT_ID"],
        broker_position_available=values["CURRENT_BROKER_POSITION_AVAILABLE"],
        broker_position_reason=values["CURRENT_BROKER_POSITION_REASON"],
        position_reconciliation_ok=values["CURRENT_POSITION_RECONCILIATION_OK"],
        position_reconciliation_action=values[
            "CURRENT_POSITION_RECONCILIATION_ACTION"
        ],
        position_reconciliation_reason=values[
            "CURRENT_POSITION_RECONCILIATION_REASON"
        ],
        broker_order_state=values["CURRENT_BROKER_ORDER_STATE"],
        broker_order_id=values["CURRENT_BROKER_ORDER_ID"],
        broker_order_status=values["CURRENT_BROKER_ORDER_STATUS"],
        broker_order_status_description=values[
            "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION"
        ],
        dispatch_status=values["CURRENT_DISPATCH_STATUS"],
        dispatch_reason=values["CURRENT_DISPATCH_REASON"],
        dispatch_id=values["CURRENT_DISPATCH_ID"],
        position_state=values["CURRENT_POSITION_STATE"],
        position_contracts=values["CURRENT_POSITION_CONTRACTS"],
        position_entry_side=values["CURRENT_POSITION_ENTRY_SIDE"],
        last_dispatch_signature=values["LAST_DISPATCH_SIGNATURE"],
        pending_order_action=values["CURRENT_PENDING_ORDER_ACTION"],
        pending_order_side=values["CURRENT_PENDING_ORDER_SIDE"],
        pending_order_quantity=values["CURRENT_PENDING_ORDER_QUANTITY"],
        pending_order_symbol=values["CURRENT_PENDING_ORDER_SYMBOL"],
        pending_order_submitted_at=values["CURRENT_PENDING_ORDER_SUBMITTED_AT"],
    )


def execution_intent_from_legacy(values: Mapping[str, Any]) -> ExecutionIntent:
    """Convert the current legacy intent globals without changing their values."""
    return ExecutionIntent(
        status=values["CURRENT_EXECUTION_STATUS"],
        action=values["CURRENT_EXECUTION_ACTION"],
        side=values["CURRENT_EXECUTION_SIDE"],
        quantity=values["CURRENT_EXECUTION_QUANTITY"],
        symbol=values["CURRENT_EXECUTION_SYMBOL"],
        order_type=values["CURRENT_EXECUTION_ORDER_TYPE"],
        reason=values["CURRENT_EXECUTION_REASON"],
    )


def execution_config_from_legacy(
    values: Mapping[str, Any],
    *,
    submission_timestamp: str | None,
) -> DispatchConfig:
    """Build the explicit modular config from the corresponding legacy globals."""
    return DispatchConfig(
        execution_mode=values["EXECUTION_MODE"],
        live_order_execution_enabled=values["LIVE_ORDER_EXECUTION_ENABLED"],
        position_reconciliation_ok=values["CURRENT_POSITION_RECONCILIATION_OK"],
        broker_account_id=values["CURRENT_BROKER_ACCOUNT_ID"],
        submission_timestamp=submission_timestamp,
    )
