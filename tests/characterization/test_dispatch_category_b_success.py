"""Único success B autorizado: ENTRY BUY con OrderID totalmente sintético."""

from __future__ import annotations

from copy import deepcopy

from tests.characterization.legacy_harness import (
    FIXED_PENDING_TIMESTAMP,
    SYNTHETIC_SUBMIT_SUCCESS,
    ForbiddenTransport,
    RecordingSuccessSubmit,
    load_dispatch_execution_category_b_failure,
    load_dispatch_execution_category_b_success,
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


def test_entry_buy_success_returns_submitted_with_synthetic_order_id() -> None:
    runtime = load_dispatch_execution_category_b_success()
    before = _state(runtime.namespace)
    expected_payload = runtime.namespace["build_tradestation_order_payload"]()

    assert expected_payload == EXPECTED_PAYLOAD
    assert runtime.namespace["validate_tradestation_order_payload"](
        expected_payload
    ) == (True, "ORDER PAYLOAD VALID")

    result = runtime.function()
    after = _state(runtime.namespace)

    assert result == {
        "status": "SUBMITTED",
        "action": "ENTRY",
        "side": "BUY",
        "quantity": 2,
        "symbol": "SYNTHETIC-ES",
        "order_type": "MARKET",
        "reason": "SYNTHETIC SUBMIT SUCCESS",
        "safety_ok": True,
        "safety_reason": "EXECUTION SAFETY CHECK PASSED",
        "broker_response": {
            "Orders": [
                {"OrderID": "SYNTHETIC-ORDER-ID-001"},
            ]
        },
        "broker_status_code": 200,
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
    assert after == {
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


def test_recording_success_submit_is_local_and_transport_free() -> None:
    submit = RecordingSuccessSubmit()
    transport = ForbiddenTransport()

    assert submit(EXPECTED_PAYLOAD) == SYNTHETIC_SUBMIT_SUCCESS
    assert submit.call_count == 1
    assert submit.payloads == [EXPECTED_PAYLOAD]
    assert transport.call_count == 0


def test_failure_and_success_dispatch_loaders_are_isolated() -> None:
    failure = load_dispatch_execution_category_b_failure()
    success = load_dispatch_execution_category_b_success()

    assert failure.namespace is not success.namespace
    assert failure.submit is not success.submit
    assert failure.transport is not success.transport
    assert failure.clock is not success.clock
    assert _state(failure.namespace) == _state(success.namespace)
    failure.namespace["LAST_DISPATCH_SIGNATURE"] = ("FAILURE-MUTATED",)
    failure.namespace["CURRENT_PENDING_ORDER_ACTION"] = "FAILURE-MUTATED"
    assert success.namespace["LAST_DISPATCH_SIGNATURE"] != ("FAILURE-MUTATED",)
    assert success.namespace["CURRENT_PENDING_ORDER_ACTION"] == "SENTINEL_ACTION"
    assert failure.submit.call_count == success.submit.call_count == 0
    assert failure.transport.call_count == success.transport.call_count == 0
    assert failure.clock.call_count == success.clock.call_count == 0

