"""Pure broker-position normalization preserved from Phase 4."""


def normalize_tradestation_es_position(position):
    if not position:
        return {
            "state": "FLAT",
            "contracts": 0,
            "entry_side": "NONE",
        }

    quantity = position.get("Quantity", 0)

    try:
        quantity = int(float(quantity))
    except (TypeError, ValueError):
        return {
            "state": "UNKNOWN",
            "contracts": 0,
            "entry_side": "NONE",
        }

    if quantity > 0:
        return {
            "state": "LONG",
            "contracts": quantity,
            "entry_side": "BUY",
        }

    if quantity < 0:
        return {
            "state": "SHORT",
            "contracts": abs(quantity),
            "entry_side": "SELL",
        }

    return {
        "state": "FLAT",
        "contracts": 0,
        "entry_side": "NONE",
    }
