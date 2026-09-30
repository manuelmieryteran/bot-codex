"""Position-state validation preserved from Phase 4."""


def validate_position_state(
    position_state,
    position_contracts,
    position_entry_side,
):
    if position_state == "FLAT":
        if position_contracts != 0:
            return False, "FLAT POSITION WITH NONZERO CONTRACTS"

        if position_entry_side != "NONE":
            return False, "FLAT POSITION WITH ENTRY SIDE"

    elif position_state == "LONG":
        if position_contracts <= 0:
            return False, "LONG POSITION WITH INVALID CONTRACTS"

        if position_entry_side != "BUY":
            return False, "LONG POSITION WITH INVALID ENTRY SIDE"

    elif position_state == "SHORT":
        if position_contracts <= 0:
            return False, "SHORT POSITION WITH INVALID CONTRACTS"

        if position_entry_side != "SELL":
            return False, "SHORT POSITION WITH INVALID ENTRY SIDE"

    else:
        return False, "UNKNOWN POSITION STATE"

    return True, "POSITION STATE VALID"
