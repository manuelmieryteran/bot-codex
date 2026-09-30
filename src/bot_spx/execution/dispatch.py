"""Pure execution-dispatch transitions with external work represented as effects."""

from dataclasses import replace

from bot_spx.execution.dispatch_models import (
    DispatchConfig,
    DispatchEffect,
    DispatchTransition,
    ExecutionIntent,
    ExecutionState,
)
from bot_spx.execution.execution_safety import execution_safety_check
from bot_spx.execution.order_payload import build_tradestation_order_payload
from bot_spx.execution.payload_validation import validate_tradestation_order_payload


NO_EFFECT = DispatchEffect(kind="NONE")


def _result(intent, status, reason, safety_ok, safety_reason):
    return {
        "status": status,
        "action": intent.action,
        "side": intent.side,
        "quantity": intent.quantity,
        "symbol": intent.symbol,
        "order_type": intent.order_type,
        "reason": reason,
        "safety_ok": safety_ok,
        "safety_reason": safety_reason,
    }


def dispatch_transition(state, intent, config):
    safety_ok, safety_reason = execution_safety_check(
        config.execution_mode,
        config.live_order_execution_enabled,
        config.position_reconciliation_ok,
        intent.status,
        intent.action,
        intent.side,
        intent.quantity,
        state.position_state,
        state.position_contracts,
        state.position_entry_side,
    )

    if intent.status != "READY":
        new_state = replace(state, last_dispatch_signature=None)
        result = _result(
            replace(intent, action="NONE", side="NONE", quantity=0),
            "IDLE",
            "NO EXECUTION REQUEST",
            safety_ok,
            safety_reason,
        )
        return DispatchTransition(new_state, NO_EFFECT, result)

    if state.broker_order_state in ("OPEN", "UNKNOWN"):
        result = _result(
            intent,
            "ORDER_BLOCKED",
            f"ORDER BLOCKED: BROKER ORDER STATE {state.broker_order_state}",
            safety_ok,
            safety_reason,
        )
        return DispatchTransition(state, NO_EFFECT, result)

    if intent.action == "ENTRY" and state.position_state != "FLAT":
        result = _result(
            intent,
            "POSITION_BLOCKED",
            f"ENTRY BLOCKED: POSITION STATE {state.position_state}",
            safety_ok,
            safety_reason,
        )
        return DispatchTransition(state, NO_EFFECT, result)

    if intent.action == "EXIT" and state.position_state == "FLAT":
        result = _result(
            intent,
            "POSITION_BLOCKED",
            "EXIT BLOCKED: POSITION STATE FLAT",
            safety_ok,
            safety_reason,
        )
        return DispatchTransition(state, NO_EFFECT, result)

    signature = (intent.action, intent.side, intent.quantity, intent.reason)

    if signature == state.last_dispatch_signature:
        result = _result(
            intent,
            "DUPLICATE_BLOCKED",
            "DUPLICATE EXECUTION INTENT",
            safety_ok,
            safety_reason,
        )
        return DispatchTransition(state, NO_EFFECT, result)

    if config.execution_mode == "DRY_RUN":
        new_state = replace(state, last_dispatch_signature=signature)

        if intent.action == "ENTRY":
            if intent.side == "BUY":
                new_state = replace(
                    new_state,
                    position_state="LONG",
                    position_entry_side="BUY",
                )
            elif intent.side == "SELL":
                new_state = replace(
                    new_state,
                    position_state="SHORT",
                    position_entry_side="SELL",
                )
            new_state = replace(new_state, position_contracts=intent.quantity)

        elif intent.action == "EXIT":
            new_state = replace(
                new_state,
                position_state="FLAT",
                position_contracts=0,
                position_entry_side="NONE",
            )

        result = _result(
            intent,
            "SIMULATED",
            "DRY RUN EXECUTION SIMULATED",
            safety_ok,
            safety_reason,
        )
        return DispatchTransition(new_state, NO_EFFECT, result)

    if not safety_ok:
        result = _result(intent, "BLOCKED", safety_reason, False, safety_reason)
        return DispatchTransition(state, NO_EFFECT, result)

    payload = build_tradestation_order_payload(
        intent.action,
        intent.side,
        intent.quantity,
        config.broker_account_id,
        intent.symbol,
        intent.order_type,
        state.position_state,
        state.position_contracts,
    )
    payload_valid, payload_reason = validate_tradestation_order_payload(payload)

    if not payload_valid:
        result = _result(
            intent,
            "PAYLOAD_BLOCKED",
            payload_reason,
            True,
            safety_reason,
        )
        return DispatchTransition(state, NO_EFFECT, result)

    if config.submission_timestamp is None:
        raise ValueError("SUBMISSION TIMESTAMP REQUIRED")

    new_state = replace(
        state,
        last_dispatch_signature=signature,
        pending_order_action=intent.action,
        pending_order_side=payload["TradeAction"],
        pending_order_quantity=int(payload["Quantity"]),
        pending_order_symbol=intent.symbol,
        pending_order_submitted_at=config.submission_timestamp,
    )
    return DispatchTransition(
        new_state,
        DispatchEffect(kind="SUBMIT_ORDER", payload=payload),
        {},
    )


def complete_submit_effect(state, intent, safety_reason, submit_result):
    result = {
        "status": "SUBMITTED" if submit_result.get("ok") else "SUBMIT_FAILED",
        "action": intent.action,
        "side": intent.side,
        "quantity": intent.quantity,
        "symbol": intent.symbol,
        "order_type": intent.order_type,
        "reason": submit_result.get("reason", "ORDER SUBMISSION RESULT UNKNOWN"),
        "safety_ok": True,
        "safety_reason": safety_reason,
        "broker_response": submit_result.get("response"),
        "broker_status_code": submit_result.get("status_code"),
        "pending_order_action": state.pending_order_action,
        "pending_order_side": state.pending_order_side,
        "pending_order_quantity": state.pending_order_quantity,
        "pending_order_symbol": state.pending_order_symbol,
        "pending_order_submitted_at": state.pending_order_submitted_at,
    }
    return DispatchTransition(state, NO_EFFECT, result)
