"""Caracterización aislada de payloads, endpoints y la tercera barrera."""

from __future__ import annotations

from copy import deepcopy

import pytest

from tests.characterization.legacy_harness import (
    load_get_tradestation_api_base_url,
    load_submit_tradestation_order,
    load_validate_tradestation_order_payload,
)
from tests.characterization.test_execution_guardrails import SYNTHETIC_VALID_PAYLOAD


SYNTHETIC_LIVE_URL = "https://synthetic-live.invalid"
SYNTHETIC_SIM_URL = "https://synthetic-sim.invalid"


def _payload_with(**changes: object) -> dict[str, object]:
    payload = deepcopy(SYNTHETIC_VALID_PAYLOAD)
    payload.update(changes)
    return payload


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (SYNTHETIC_VALID_PAYLOAD, (True, "ORDER PAYLOAD VALID")),
        (None, (False, "ORDER PAYLOAD IS NONE")),
        ([], (False, "MISSING ORDER FIELD: AccountID")),
        (_payload_with(AccountID=None), (False, "ACCOUNT ID NOT AVAILABLE")),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "AccountID"},
            (False, "MISSING ORDER FIELD: AccountID"),
        ),
        (_payload_with(Symbol=""), (False, "INVALID ORDER SYMBOL")),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "Symbol"},
            (False, "MISSING ORDER FIELD: Symbol"),
        ),
        (_payload_with(Quantity="0"), (False, "INVALID ORDER QUANTITY")),
        (_payload_with(Quantity="ABC"), (False, "INVALID ORDER QUANTITY")),
        (_payload_with(Quantity="-1"), (False, "INVALID ORDER QUANTITY")),
        (_payload_with(Quantity="1.5"), (False, "INVALID ORDER QUANTITY")),
        (_payload_with(Quantity=True), (True, "ORDER PAYLOAD VALID")),
        (_payload_with(TradeAction="HOLD"), (False, "INVALID TRADE ACTION")),
        (_payload_with(OrderType="LIMIT"), (False, "UNSUPPORTED ORDER TYPE")),
        (_payload_with(TimeInForce="DAY"), (False, "INVALID TIME IN FORCE")),
        (
            _payload_with(TimeInForce={"Duration": "GTC"}),
            (False, "UNSUPPORTED TIME IN FORCE"),
        ),
        (_payload_with(TimeInForce={}), (False, "UNSUPPORTED TIME IN FORCE")),
        (_payload_with(Route="SyntheticRoute"), (False, "UNSUPPORTED ROUTE")),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "Quantity"},
            (False, "MISSING ORDER FIELD: Quantity"),
        ),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "OrderType"},
            (False, "MISSING ORDER FIELD: OrderType"),
        ),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "TradeAction"},
            (False, "MISSING ORDER FIELD: TradeAction"),
        ),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "TimeInForce"},
            (False, "MISSING ORDER FIELD: TimeInForce"),
        ),
        (
            {key: value for key, value in SYNTHETIC_VALID_PAYLOAD.items() if key != "Route"},
            (False, "MISSING ORDER FIELD: Route"),
        ),
    ],
    ids=[
        "valid",
        "none",
        "non-dict-list",
        "account-none",
        "account-missing",
        "symbol-empty",
        "symbol-missing",
        "quantity-zero",
        "quantity-nonnumeric",
        "quantity-negative",
        "quantity-decimal-string",
        "quantity-bool-currently-accepted",
        "trade-action-invalid",
        "order-type-invalid",
        "time-in-force-not-dict",
        "time-in-force-duration-invalid",
        "time-in-force-duration-missing",
        "route-invalid",
        "quantity-missing",
        "order-type-missing",
        "trade-action-missing",
        "time-in-force-missing",
        "route-missing",
    ],
)
def test_validate_order_payload_characterization(
    payload: object,
    expected: tuple[bool, str],
) -> None:
    isolated = load_validate_tradestation_order_payload()

    assert isolated.function(payload) == expected
    assert isolated.transport.call_count == 0


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ("SIM", SYNTHETIC_SIM_URL),
        ("LIVE", SYNTHETIC_LIVE_URL),
    ],
)
def test_api_base_url_selects_synthetic_endpoint(
    environment: str,
    expected: str,
) -> None:
    isolated = load_get_tradestation_api_base_url(
        order_execution_environment=environment,
        live_api_base_url=SYNTHETIC_LIVE_URL,
        sim_api_base_url=SYNTHETIC_SIM_URL,
    )

    assert isolated.function() == expected
    assert isolated.transport.call_count == 0


def test_api_base_url_rejects_unknown_environment_exactly() -> None:
    isolated = load_get_tradestation_api_base_url(
        order_execution_environment="SYNTHETIC_UNKNOWN",
        live_api_base_url=SYNTHETIC_LIVE_URL,
        sim_api_base_url=SYNTHETIC_SIM_URL,
    )

    with pytest.raises(ValueError, match="^INVALID ORDER EXECUTION ENVIRONMENT$"):
        isolated.function()

    assert isolated.transport.call_count == 0


def test_invalid_payload_blocks_before_transport_with_synthetic_live_enabled() -> None:
    isolated = load_submit_tradestation_order(
        live_order_execution_enabled=True,
        order_execution_environment="SIM",
    )
    invalid_payload = _payload_with(Quantity="0")

    result = isolated.function(invalid_payload)

    assert result == {
        "ok": False,
        "status_code": None,
        "reason": "INVALID ORDER QUANTITY",
        "response": None,
    }
    assert isolated.transport.call_count == 0


def test_synthetic_endpoints_and_live_override_are_namespace_local() -> None:
    endpoint = load_get_tradestation_api_base_url(
        order_execution_environment="SIM",
        live_api_base_url=SYNTHETIC_LIVE_URL,
        sim_api_base_url=SYNTHETIC_SIM_URL,
    )
    clean_submit = load_submit_tradestation_order()

    assert endpoint.namespace["TS_SIM_API_BASE_URL"] == SYNTHETIC_SIM_URL
    assert "TS_SIM_API_BASE_URL" not in clean_submit.namespace
    assert clean_submit.namespace["LIVE_ORDER_EXECUTION_ENABLED"] is False
    assert endpoint.namespace is not clean_submit.namespace
    assert endpoint.transport is not clean_submit.transport
