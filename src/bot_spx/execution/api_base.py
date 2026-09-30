"""TradeStation API-base selection preserved from Phase 4."""


def get_tradestation_api_base_url(
    order_execution_environment,
    live_api_base_url,
    sim_api_base_url,
):
    if order_execution_environment == "LIVE":
        return live_api_base_url

    if order_execution_environment == "SIM":
        return sim_api_base_url

    raise ValueError("INVALID ORDER EXECUTION ENVIRONMENT")
