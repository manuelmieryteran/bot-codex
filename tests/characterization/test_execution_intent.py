"""Caracterización de posición e intención, sin dispatch, submit ni red."""

from __future__ import annotations

import pytest

from tests.characterization.legacy_harness import (
    load_build_execution_intent,
    load_build_tradestation_order_payload,
    load_validate_position_state,
)


SYNTHETIC_ACCOUNT = "SYNTHETIC-ACCOUNT"
SYNTHETIC_SYMBOL = "SYNTHETIC-ES"


def _intent_snapshot(namespace: dict[str, object]) -> dict[str, object]:
    """Lee los globals mutados; no replica ninguna decisión del baseline."""
    return {
        "status": namespace["CURRENT_EXECUTION_STATUS"],
        "action": namespace["CURRENT_EXECUTION_ACTION"],
        "reason": namespace["CURRENT_EXECUTION_REASON"],
        "symbol": namespace["CURRENT_EXECUTION_SYMBOL"],
        "side": namespace["CURRENT_EXECUTION_SIDE"],
        "quantity": namespace["CURRENT_EXECUTION_QUANTITY"],
        "order_type": namespace["CURRENT_EXECUTION_ORDER_TYPE"],
    }


def _expected_intent(
    *,
    status: str = "IDLE",
    action: str = "NONE",
    reason: str = "NO EXECUTION REQUEST",
    side: str = "NONE",
    quantity: int = 0,
) -> dict[str, object]:
    return {
        "status": status,
        "action": action,
        "reason": reason,
        "symbol": SYNTHETIC_SYMBOL,
        "side": side,
        "quantity": quantity,
        "order_type": "MARKET",
    }


@pytest.mark.parametrize(
    ("state", "contracts", "entry_side", "expected"),
    [
        ("FLAT", 0, "NONE", (True, "POSITION STATE VALID")),
        ("FLAT", 1, "NONE", (False, "FLAT POSITION WITH NONZERO CONTRACTS")),
        ("FLAT", 0, "BUY", (False, "FLAT POSITION WITH ENTRY SIDE")),
        ("LONG", 1, "BUY", (True, "POSITION STATE VALID")),
        ("LONG", 3, "BUY", (True, "POSITION STATE VALID")),
        ("LONG", 0, "BUY", (False, "LONG POSITION WITH INVALID CONTRACTS")),
        ("LONG", 1, "SELL", (False, "LONG POSITION WITH INVALID ENTRY SIDE")),
        ("SHORT", 1, "SELL", (True, "POSITION STATE VALID")),
        ("SHORT", 3, "SELL", (True, "POSITION STATE VALID")),
        ("SHORT", 0, "SELL", (False, "SHORT POSITION WITH INVALID CONTRACTS")),
        ("SHORT", 1, "BUY", (False, "SHORT POSITION WITH INVALID ENTRY SIDE")),
        ("SYNTHETIC_UNKNOWN", 0, "NONE", (False, "UNKNOWN POSITION STATE")),
    ],
)
def test_validate_position_state_exactly(
    state: str,
    contracts: int,
    entry_side: str,
    expected: tuple[bool, str],
) -> None:
    isolated = load_validate_position_state(
        position_state=state,
        position_contracts=contracts,
        position_entry_side=entry_side,
    )

    assert isolated.function() == expected
    assert isolated.transport.call_count == 0


@pytest.mark.parametrize(
    (
        "case",
        "signal",
        "entry_permission",
        "exit_permission",
        "expected",
    ),
    [
        (
            "long-entry",
            "LONG MEAN REVERSION",
            True,
            False,
            _expected_intent(
                status="READY",
                action="ENTRY",
                reason="LONG MEAN REVERSION",
                side="BUY",
                quantity=2,
            ),
        ),
        (
            "short-entry",
            "SHORT BREAKDOWN",
            True,
            False,
            _expected_intent(
                status="READY",
                action="ENTRY",
                reason="SHORT BREAKDOWN",
                side="SELL",
                quantity=2,
            ),
        ),
        (
            "long-exit",
            "FORCED EXIT",
            False,
            True,
            _expected_intent(
                status="READY",
                action="EXIT",
                reason="FORCED EXIT",
                side="FLATTEN",
            ),
        ),
        (
            "short-exit",
            "FORCED EXIT",
            False,
            True,
            _expected_intent(
                status="READY",
                action="EXIT",
                reason="FORCED EXIT",
                side="FLATTEN",
            ),
        ),
        ("no-permissions", "LONG BREAKOUT", False, False, _expected_intent()),
        ("signal-none", "NONE", True, False, _expected_intent()),
        ("signal-unknown", "SYNTHETIC_UNKNOWN", True, False, _expected_intent()),
        (
            "entry-precedes-exit",
            "LONG BREAKOUT",
            True,
            True,
            _expected_intent(
                status="READY",
                action="ENTRY",
                reason="LONG BREAKOUT",
                side="BUY",
                quantity=2,
            ),
        ),
        (
            "unrecognized-entry-permission-suppresses-exit",
            "SYNTHETIC_UNKNOWN",
            True,
            True,
            _expected_intent(),
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_build_execution_intent_exactly(
    case: str,
    signal: str,
    entry_permission: bool,
    exit_permission: bool,
    expected: dict[str, object],
) -> None:
    isolated = load_build_execution_intent(
        confirmed_signal=signal,
        entry_execution_permission=entry_permission,
        exit_execution_permission=exit_permission,
        position_size_contracts=2,
        symbol=SYNTHETIC_SYMBOL,
    )

    assert isolated.function() is None, case
    assert _intent_snapshot(isolated.namespace) == expected
    assert isolated.transport.call_count == 0


@pytest.mark.parametrize(
    (
        "signal",
        "entry_permission",
        "exit_permission",
        "position_state",
        "position_contracts",
        "expected_intent",
        "expected_trade_action",
        "expected_quantity",
    ),
    [
        (
            "LONG MEAN REVERSION",
            True,
            False,
            "FLAT",
            0,
            _expected_intent(
                status="READY",
                action="ENTRY",
                reason="LONG MEAN REVERSION",
                side="BUY",
                quantity=2,
            ),
            "BUY",
            "2",
        ),
        (
            "SHORT BREAKDOWN",
            True,
            False,
            "FLAT",
            0,
            _expected_intent(
                status="READY",
                action="ENTRY",
                reason="SHORT BREAKDOWN",
                side="SELL",
                quantity=2,
            ),
            "SELL",
            "2",
        ),
        (
            "FORCED EXIT",
            False,
            True,
            "LONG",
            3,
            _expected_intent(
                status="READY",
                action="EXIT",
                reason="FORCED EXIT",
                side="FLATTEN",
            ),
            "SELL",
            "3",
        ),
        (
            "FORCED EXIT",
            False,
            True,
            "SHORT",
            3,
            _expected_intent(
                status="READY",
                action="EXIT",
                reason="FORCED EXIT",
                side="FLATTEN",
            ),
            "BUY",
            "3",
        ),
    ],
    ids=["long-entry-chain", "short-entry-chain", "long-exit-chain", "short-exit-chain"],
)
def test_intent_to_payload_to_validation_chain(
    signal: str,
    entry_permission: bool,
    exit_permission: bool,
    position_state: str,
    position_contracts: int,
    expected_intent: dict[str, object],
    expected_trade_action: str,
    expected_quantity: str,
) -> None:
    intent_runtime = load_build_execution_intent(
        confirmed_signal=signal,
        entry_execution_permission=entry_permission,
        exit_execution_permission=exit_permission,
        position_size_contracts=2,
        symbol=SYNTHETIC_SYMBOL,
    )
    assert intent_runtime.function() is None
    intent = _intent_snapshot(intent_runtime.namespace)
    assert intent == expected_intent

    # Puente explícito entre las interfaces globales legacy: los campos de la
    # intención alimentan los globals del builder; la posición abierta sigue
    # siendo una entrada separada porque EXIT toma de ella su quantity/side.
    payload_runtime = load_build_tradestation_order_payload(
        execution_action=str(intent["action"]),
        execution_side=str(intent["side"]),
        execution_quantity=int(intent["quantity"]),
        position_state=position_state,
        position_contracts=position_contracts,
        account_id=SYNTHETIC_ACCOUNT,
        symbol=str(intent["symbol"]),
        order_type=str(intent["order_type"]),
    )
    payload = payload_runtime.function()

    assert payload == {
        "AccountID": SYNTHETIC_ACCOUNT,
        "Symbol": SYNTHETIC_SYMBOL,
        "Quantity": expected_quantity,
        "OrderType": "MARKET",
        "TradeAction": expected_trade_action,
        "TimeInForce": {"Duration": "DAY"},
        "Route": "Intelligent",
    }
    assert payload_runtime.namespace["validate_tradestation_order_payload"](payload) == (
        True,
        "ORDER PAYLOAD VALID",
    )
    assert intent_runtime.transport.call_count == 0
    assert payload_runtime.transport.call_count == 0


def test_position_and_intent_namespaces_are_isolated() -> None:
    position = load_validate_position_state(
        position_state="LONG",
        position_contracts=3,
        position_entry_side="BUY",
    )
    intent = load_build_execution_intent(
        confirmed_signal="NONE",
        entry_execution_permission=False,
        exit_execution_permission=False,
        position_size_contracts=2,
        symbol=SYNTHETIC_SYMBOL,
    )

    assert position.namespace is not intent.namespace
    assert position.transport is not intent.transport
    assert "CURRENT_CONFIRMED_SIGNAL" not in position.namespace
    assert "CURRENT_POSITION_STATE" not in intent.namespace
    assert position.transport.call_count == intent.transport.call_count == 0

