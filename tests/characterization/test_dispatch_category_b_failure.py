"""Única rama B autorizada: ENTRY BUY y fallo local conocido de submit."""

from __future__ import annotations

from copy import deepcopy

from tests.characterization.legacy_harness import (
    FIXED_PENDING_TIMESTAMP,
    SYNTHETIC_SUBMIT_FAILURE,
    FixedClock,
    ForbiddenTransport,
    RecordingSubmit,
    load_dispatch_execution_category_b_failure,
)


EXPECTED_PAYLOAD = {
    "AccountID": "SYNTHETIC-ACCOUNT",
    "Symbol": "SYNTHETIC-ES",
    "Quantity": "2",
    "OrderType": "MARKET",
    "TradeAction": "BUY",
    "TimeInForce": {"Duration": "DAY"},
    "Route": "Intelligent",
}
MUTABLE_NAMES = (
    "LAST_DISPATCH_SIGNATURE",
    "CURRENT_POSITION_STATE",
    "CURRENT_POSITION_CONTRACTS",
    "CURRENT_POSITION_ENTRY_SIDE",
    "CURRENT_PENDING_ORDER_ACTION",
    "CURRENT_PENDING_ORDER_SIDE",
    "CURRENT_PENDING_ORDER_QUANTITY",
    "CURRENT_PENDING_ORDER_SYMBOL",
    "CURRENT_PENDING_ORDER_SUBMITTED_AT",
)


def _state(namespace: dict[str, object]) -> dict[str, object]:
    return {name: deepcopy(namespace[name]) for name in MUTABLE_NAMES}


def test_entry_buy_submit_failure_consumes_signature_and_keeps_pending() -> None:
    runtime = load_dispatch_execution_category_b_failure()
    before = _state(runtime.namespace)

    payload = runtime.namespace["build_tradestation_order_payload"]()
    assert payload == EXPECTED_PAYLOAD
    assert runtime.namespace["validate_tradestation_order_payload"](payload) == (
        True,
        "ORDER PAYLOAD VALID",
    )

    first_result = runtime.function()
    after_failure = _state(runtime.namespace)

    assert first_result == {
        "status": "SUBMIT_FAILED",
        "action": "ENTRY",
        "side": "BUY",
        "quantity": 2,
        "symbol": "SYNTHETIC-ES",
        "order_type": "MARKET",
        "reason": "SYNTHETIC SUBMIT FAILURE",
        "safety_ok": True,
        "safety_reason": "EXECUTION SAFETY CHECK PASSED",
        "broker_response": {"synthetic": True},
        "broker_status_code": 503,
        "pending_order_action": "ENTRY",
        "pending_order_side": "BUY",
        "pending_order_quantity": 2,
        "pending_order_symbol": "SYNTHETIC-ES",
        "pending_order_submitted_at": FIXED_PENDING_TIMESTAMP,
    }
    assert runtime.submit.call_count == 1
    assert runtime.submit.payloads == [EXPECTED_PAYLOAD]
    assert runtime.clock.call_count == 1
    assert runtime.transport.call_count == 0
    assert before == {
        "LAST_DISPATCH_SIGNATURE": (
            "PREVIOUS",
            "NONE",
            99,
            "PREVIOUS REASON",
        ),
        "CURRENT_POSITION_STATE": "FLAT",
        "CURRENT_POSITION_CONTRACTS": 0,
        "CURRENT_POSITION_ENTRY_SIDE": "NONE",
        "CURRENT_PENDING_ORDER_ACTION": "SENTINEL_ACTION",
        "CURRENT_PENDING_ORDER_SIDE": "SENTINEL_SIDE",
        "CURRENT_PENDING_ORDER_QUANTITY": 91,
        "CURRENT_PENDING_ORDER_SYMBOL": "SENTINEL_SYMBOL",
        "CURRENT_PENDING_ORDER_SUBMITTED_AT": "SENTINEL_TIME",
    }
    assert after_failure == {
        "LAST_DISPATCH_SIGNATURE": (
            "ENTRY",
            "BUY",
            2,
            "LONG MEAN REVERSION",
        ),
        "CURRENT_POSITION_STATE": "FLAT",
        "CURRENT_POSITION_CONTRACTS": 0,
        "CURRENT_POSITION_ENTRY_SIDE": "NONE",
        "CURRENT_PENDING_ORDER_ACTION": "ENTRY",
        "CURRENT_PENDING_ORDER_SIDE": "BUY",
        "CURRENT_PENDING_ORDER_QUANTITY": 2,
        "CURRENT_PENDING_ORDER_SYMBOL": "SYNTHETIC-ES",
        "CURRENT_PENDING_ORDER_SUBMITTED_AT": FIXED_PENDING_TIMESTAMP,
    }

    second_result = runtime.function()

    assert second_result == {
        "status": "DUPLICATE_BLOCKED",
        "action": "ENTRY",
        "side": "BUY",
        "quantity": 2,
        "symbol": "SYNTHETIC-ES",
        "order_type": "MARKET",
        "reason": "DUPLICATE EXECUTION INTENT",
        "safety_ok": True,
        "safety_reason": "EXECUTION SAFETY CHECK PASSED",
    }
    assert _state(runtime.namespace) == after_failure
    assert runtime.submit.call_count == 1
    assert runtime.clock.call_count == 1
    assert runtime.transport.call_count == 0


def test_recording_submit_is_local_deterministic_and_transport_free() -> None:
    submit = RecordingSubmit()
    transport = ForbiddenTransport()

    assert submit(EXPECTED_PAYLOAD) == SYNTHETIC_SUBMIT_FAILURE
    assert submit.call_count == 1
    assert submit.payloads == [EXPECTED_PAYLOAD]
    assert transport.call_count == 0


def test_fixed_clock_is_deterministic() -> None:
    clock = FixedClock()

    assert clock.call_count == 0
    instant = clock.now("SYNTHETIC-MARKET-TZ")
    assert clock.call_count == 1
    assert instant.isoformat() == FIXED_PENDING_TIMESTAMP


def test_category_b_loads_are_isolated_without_executing_dispatch() -> None:
    first = load_dispatch_execution_category_b_failure()
    second = load_dispatch_execution_category_b_failure()

    assert first.namespace is not second.namespace
    assert first.submit is not second.submit
    assert first.transport is not second.transport
    assert first.clock is not second.clock
    assert _state(first.namespace) == _state(second.namespace)
    first.namespace["LAST_DISPATCH_SIGNATURE"] = ("MUTATED",)
    first.namespace["CURRENT_PENDING_ORDER_ACTION"] = "MUTATED"
    assert second.namespace["LAST_DISPATCH_SIGNATURE"] != ("MUTATED",)
    assert second.namespace["CURRENT_PENDING_ORDER_ACTION"] == "SENTINEL_ACTION"
    assert first.submit.call_count == second.submit.call_count == 0
    assert first.transport.call_count == second.transport.call_count == 0
    assert first.clock.call_count == second.clock.call_count == 0

