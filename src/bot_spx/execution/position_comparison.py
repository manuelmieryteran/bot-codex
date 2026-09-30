"""Pure internal-versus-broker position comparison preserved from Phase 4."""

from bot_spx.execution.broker_position import normalize_tradestation_es_position


def compare_internal_vs_broker_position(
    position_state,
    position_contracts,
    position_entry_side,
    broker_position,
):
    normalized = normalize_tradestation_es_position(broker_position)
    broker_state = normalized["state"]
    broker_contracts = normalized["contracts"]
    broker_entry_side = normalized["entry_side"]

    if broker_state == "UNKNOWN":
        return {
            "match": False,
            "reason": "BROKER POSITION UNKNOWN",
            "broker_state": broker_state,
            "broker_contracts": broker_contracts,
            "broker_entry_side": broker_entry_side,
        }

    if (
        position_state == broker_state
        and position_contracts == broker_contracts
        and position_entry_side == broker_entry_side
    ):
        return {
            "match": True,
            "reason": "INTERNAL AND BROKER POSITION MATCH",
            "broker_state": broker_state,
            "broker_contracts": broker_contracts,
            "broker_entry_side": broker_entry_side,
        }

    return {
        "match": False,
        "reason": "INTERNAL AND BROKER POSITION MISMATCH",
        "broker_state": broker_state,
        "broker_contracts": broker_contracts,
        "broker_entry_side": broker_entry_side,
    }
