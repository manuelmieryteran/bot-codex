"""TradeStation order-payload construction preserved from Phase 4."""


def build_tradestation_order_payload(
    execution_action,
    execution_side,
    execution_quantity,
    account_id,
    symbol,
    order_type,
    position_state,
    position_contracts,
):
    if execution_action == "ENTRY":
        trade_action = "BUY" if execution_side == "BUY" else "SELL"

        return {
            "AccountID": account_id,
            "Symbol": symbol,
            "Quantity": str(execution_quantity),
            "OrderType": order_type,
            "TradeAction": trade_action,
            "TimeInForce": {"Duration": "DAY"},
            "Route": "Intelligent",
        }

    if execution_action == "EXIT":
        return {
            "AccountID": account_id,
            "Symbol": symbol,
            "Quantity": str(position_contracts),
            "OrderType": order_type,
            "TradeAction": "SELL" if position_state == "LONG" else "BUY",
            "TimeInForce": {"Duration": "DAY"},
            "Route": "Intelligent",
        }

    return None
