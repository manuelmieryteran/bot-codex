"""Execution-intent construction preserved from Phase 4."""


def build_execution_intent(
    confirmed_signal,
    entry_execution_permission,
    exit_execution_permission,
    position_size_contracts,
    symbol,
):
    intent = {
        "status": "IDLE",
        "action": "NONE",
        "reason": "NO EXECUTION REQUEST",
        "symbol": symbol,
        "side": "NONE",
        "quantity": 0,
        "order_type": "MARKET",
    }

    if entry_execution_permission:
        if confirmed_signal in (
            "LONG MEAN REVERSION",
            "LONG BREAKOUT",
        ):
            intent.update(
                status="READY",
                action="ENTRY",
                reason=confirmed_signal,
                side="BUY",
                quantity=position_size_contracts,
            )

        elif confirmed_signal in (
            "SHORT MEAN REVERSION",
            "SHORT BREAKDOWN",
        ):
            intent.update(
                status="READY",
                action="ENTRY",
                reason=confirmed_signal,
                side="SELL",
                quantity=position_size_contracts,
            )

    elif exit_execution_permission:
        intent.update(
            status="READY",
            action="EXIT",
            reason="FORCED EXIT",
            side="FLATTEN",
            quantity=0,
        )

    return intent
