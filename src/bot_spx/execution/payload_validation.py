"""TradeStation order-payload validation preserved from Phase 4."""


def validate_tradestation_order_payload(payload):

    if payload is None:
        return False, "ORDER PAYLOAD IS NONE"

    required_fields = (
        "AccountID",
        "Symbol",
        "Quantity",
        "OrderType",
        "TradeAction",
        "TimeInForce",
        "Route",
    )

    for field in required_fields:
        if field not in payload:
            return False, f"MISSING ORDER FIELD: {field}"

    if not payload["Symbol"]:
        return False, "INVALID ORDER SYMBOL"

    try:
        quantity = int(payload["Quantity"])
    except (TypeError, ValueError):
        return False, "INVALID ORDER QUANTITY"

    if quantity <= 0:
        return False, "INVALID ORDER QUANTITY"

    if payload["OrderType"] != "MARKET":
        return False, "UNSUPPORTED ORDER TYPE"

    if payload["TradeAction"] not in (
        "BUY",
        "SELL",
    ):
        return False, "INVALID TRADE ACTION"

    if not isinstance(payload["TimeInForce"], dict):
        return False, "INVALID TIME IN FORCE"

    if payload["TimeInForce"].get("Duration") != "DAY":
        return False, "UNSUPPORTED TIME IN FORCE"

    if payload["Route"] != "Intelligent":
        return False, "UNSUPPORTED ROUTE"

    if payload["AccountID"] is None:
        return False, "ACCOUNT ID NOT AVAILABLE"

    return True, "ORDER PAYLOAD VALID"
