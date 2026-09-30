"""Caracterización de intención sintética → payload → validación de Fase 4."""

from __future__ import annotations

import pytest

from tests.characterization.legacy_harness import (
    load_build_tradestation_order_payload,
)


SYNTHETIC_ACCOUNT = "SYNTHETIC-ACCOUNT"
SYNTHETIC_SYMBOL = "SYNTHETIC-ES"


def _expected_payload(*, quantity: str, trade_action: str) -> dict[str, object]:
    return {
        "AccountID": SYNTHETIC_ACCOUNT,
        "Symbol": SYNTHETIC_SYMBOL,
        "Quantity": quantity,
        "OrderType": "MARKET",
        "TradeAction": trade_action,
        "TimeInForce": {"Duration": "DAY"},
        "Route": "Intelligent",
    }


@pytest.mark.parametrize(
    (
        "execution_action",
        "execution_side",
        "position_state",
        "expected",
    ),
    [
        ("ENTRY", "BUY", "FLAT", _expected_payload(quantity="2", trade_action="BUY")),
        ("ENTRY", "SELL", "FLAT", _expected_payload(quantity="2", trade_action="SELL")),
        ("EXIT", "NONE", "LONG", _expected_payload(quantity="3", trade_action="SELL")),
        ("EXIT", "NONE", "SHORT", _expected_payload(quantity="3", trade_action="BUY")),
        ("SYNTHETIC_UNSUPPORTED", "BUY", "FLAT", None),
    ],
    ids=[
        "entry-buy",
        "entry-sell",
        "exit-long",
        "exit-short",
        "unsupported-action",
    ],
)
def test_build_payload_and_validate_exact_contract(
    execution_action: str,
    execution_side: str,
    position_state: str,
    expected: dict[str, object] | None,
) -> None:
    isolated = load_build_tradestation_order_payload(
        execution_action=execution_action,
        execution_side=execution_side,
        execution_quantity=2,
        position_state=position_state,
        position_contracts=3,
        account_id=SYNTHETIC_ACCOUNT,
        symbol=SYNTHETIC_SYMBOL,
    )

    payload = isolated.function()

    assert payload == expected
    if expected is not None:
        assert isolated.namespace["validate_tradestation_order_payload"](payload) == (
            True,
            "ORDER PAYLOAD VALID",
        )
    assert isolated.transport.call_count == 0


def test_build_payload_loads_are_isolated() -> None:
    first = load_build_tradestation_order_payload(
        execution_action="ENTRY",
        execution_side="BUY",
        execution_quantity=2,
        position_state="FLAT",
        position_contracts=0,
        account_id=SYNTHETIC_ACCOUNT,
        symbol=SYNTHETIC_SYMBOL,
    )
    second = load_build_tradestation_order_payload(
        execution_action="ENTRY",
        execution_side="SELL",
        execution_quantity=7,
        position_state="FLAT",
        position_contracts=0,
        account_id="SYNTHETIC-ACCOUNT-SECOND",
        symbol="SYNTHETIC-ES-SECOND",
    )

    assert first.namespace is not second.namespace
    assert first.transport is not second.transport
    assert first.function()["Quantity"] == "2"
    assert second.function()["Quantity"] == "7"
    assert first.transport.call_count == second.transport.call_count == 0

