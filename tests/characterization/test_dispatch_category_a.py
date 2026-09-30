"""Characterization dinámica del dispatcher limitada a ramas categoría A."""

from __future__ import annotations

from copy import deepcopy

import pytest

from tests.characterization.legacy_harness import (
    ForbiddenClock,
    ForbiddenSubmit,
    load_dispatch_execution_category_a,
)


SYNTHETIC_SYMBOL = "SYNTHETIC-ES"
INITIAL_SIGNATURE = ("PREVIOUS", "NONE", 99, "PREVIOUS REASON")
INITIAL_PENDING = {
    "pending_order_action": "SENTINEL_ACTION",
    "pending_order_side": "SENTINEL_SIDE",
    "pending_order_quantity": 91,
    "pending_order_symbol": "SENTINEL_SYMBOL",
    "pending_order_submitted_at": "SENTINEL_TIME",
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


def _load_dispatch(**overrides: object):
    values: dict[str, object] = {
        "execution_status": "READY",
        "execution_action": "ENTRY",
        "execution_side": "BUY",
        "execution_quantity": 2,
        "execution_symbol": SYNTHETIC_SYMBOL,
        "execution_order_type": "MARKET",
        "execution_reason": "LONG MEAN REVERSION",
        "broker_order_state": "NONE",
        "position_state": "FLAT",
        "position_contracts": 0,
        "position_entry_side": "NONE",
        "execution_mode": "LIVE",
        "live_order_execution_enabled": True,
        "position_reconciliation_ok": True,
        "last_dispatch_signature": INITIAL_SIGNATURE,
        **INITIAL_PENDING,
        "broker_account_id": "SYNTHETIC-ACCOUNT",
    }
    values.update(overrides)
    return load_dispatch_execution_category_a(**values)


def _state(namespace: dict[str, object]) -> dict[str, object]:
    return {name: deepcopy(namespace[name]) for name in MUTABLE_NAMES}


def _expected_return(
    *,
    status: str,
    action: str = "ENTRY",
    side: str = "BUY",
    quantity: int = 2,
    reason: str,
    safety_ok: bool,
    safety_reason: str,
) -> dict[str, object]:
    return {
        "status": status,
        "action": action,
        "side": side,
        "quantity": quantity,
        "symbol": SYNTHETIC_SYMBOL,
        "order_type": "MARKET",
        "reason": reason,
        "safety_ok": safety_ok,
        "safety_reason": safety_reason,
    }


@pytest.mark.parametrize(
    ("case", "overrides", "expected_return", "expected_state_changes"),
    [
        (
            "idle",
            {"execution_status": "IDLE"},
            _expected_return(
                status="IDLE",
                action="NONE",
                side="NONE",
                quantity=0,
                reason="NO EXECUTION REQUEST",
                safety_ok=False,
                safety_reason="EXECUTION STATUS NOT READY",
            ),
            {"LAST_DISPATCH_SIGNATURE": None},
        ),
        (
            "broker-open",
            {"broker_order_state": "OPEN"},
            _expected_return(
                status="ORDER_BLOCKED",
                reason="ORDER BLOCKED: BROKER ORDER STATE OPEN",
                safety_ok=True,
                safety_reason="EXECUTION SAFETY CHECK PASSED",
            ),
            {},
        ),
        (
            "broker-unknown",
            {"broker_order_state": "UNKNOWN"},
            _expected_return(
                status="ORDER_BLOCKED",
                reason="ORDER BLOCKED: BROKER ORDER STATE UNKNOWN",
                safety_ok=True,
                safety_reason="EXECUTION SAFETY CHECK PASSED",
            ),
            {},
        ),
        (
            "entry-position-long",
            {
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
            _expected_return(
                status="POSITION_BLOCKED",
                reason="ENTRY BLOCKED: POSITION STATE LONG",
                safety_ok=True,
                safety_reason="EXECUTION SAFETY CHECK PASSED",
            ),
            {},
        ),
        (
            "exit-position-flat",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 0,
                "execution_reason": "FORCED EXIT",
            },
            _expected_return(
                status="POSITION_BLOCKED",
                action="EXIT",
                side="FLATTEN",
                quantity=0,
                reason="EXIT BLOCKED: POSITION STATE FLAT",
                safety_ok=True,
                safety_reason="EXECUTION SAFETY CHECK PASSED",
            ),
            {},
        ),
        (
            "duplicate",
            {
                "last_dispatch_signature": (
                    "ENTRY",
                    "BUY",
                    2,
                    "LONG MEAN REVERSION",
                )
            },
            _expected_return(
                status="DUPLICATE_BLOCKED",
                reason="DUPLICATE EXECUTION INTENT",
                safety_ok=True,
                safety_reason="EXECUTION SAFETY CHECK PASSED",
            ),
            {},
        ),
        (
            "dry-run-entry-buy",
            {
                "execution_mode": "DRY_RUN",
                "live_order_execution_enabled": False,
            },
            _expected_return(
                status="SIMULATED",
                reason="DRY RUN EXECUTION SIMULATED",
                safety_ok=False,
                safety_reason="EXECUTION MODE IS NOT LIVE",
            ),
            {
                "LAST_DISPATCH_SIGNATURE": (
                    "ENTRY",
                    "BUY",
                    2,
                    "LONG MEAN REVERSION",
                ),
                "CURRENT_POSITION_STATE": "LONG",
                "CURRENT_POSITION_CONTRACTS": 2,
                "CURRENT_POSITION_ENTRY_SIDE": "BUY",
            },
        ),
        (
            "dry-run-entry-sell",
            {
                "execution_side": "SELL",
                "execution_reason": "SHORT BREAKDOWN",
                "execution_mode": "DRY_RUN",
                "live_order_execution_enabled": False,
            },
            _expected_return(
                status="SIMULATED",
                side="SELL",
                reason="DRY RUN EXECUTION SIMULATED",
                safety_ok=False,
                safety_reason="EXECUTION MODE IS NOT LIVE",
            ),
            {
                "LAST_DISPATCH_SIGNATURE": (
                    "ENTRY",
                    "SELL",
                    2,
                    "SHORT BREAKDOWN",
                ),
                "CURRENT_POSITION_STATE": "SHORT",
                "CURRENT_POSITION_CONTRACTS": 2,
                "CURRENT_POSITION_ENTRY_SIDE": "SELL",
            },
        ),
        (
            "dry-run-exit-long",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 0,
                "execution_reason": "FORCED EXIT",
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
                "execution_mode": "DRY_RUN",
                "live_order_execution_enabled": False,
            },
            _expected_return(
                status="SIMULATED",
                action="EXIT",
                side="FLATTEN",
                quantity=0,
                reason="DRY RUN EXECUTION SIMULATED",
                safety_ok=False,
                safety_reason="EXECUTION MODE IS NOT LIVE",
            ),
            {
                "LAST_DISPATCH_SIGNATURE": (
                    "EXIT",
                    "FLATTEN",
                    0,
                    "FORCED EXIT",
                ),
                "CURRENT_POSITION_STATE": "FLAT",
                "CURRENT_POSITION_CONTRACTS": 0,
                "CURRENT_POSITION_ENTRY_SIDE": "NONE",
            },
        ),
        (
            "dry-run-exit-short",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 0,
                "execution_reason": "FORCED EXIT",
                "position_state": "SHORT",
                "position_contracts": 3,
                "position_entry_side": "SELL",
                "execution_mode": "DRY_RUN",
                "live_order_execution_enabled": False,
            },
            _expected_return(
                status="SIMULATED",
                action="EXIT",
                side="FLATTEN",
                quantity=0,
                reason="DRY RUN EXECUTION SIMULATED",
                safety_ok=False,
                safety_reason="EXECUTION MODE IS NOT LIVE",
            ),
            {
                "LAST_DISPATCH_SIGNATURE": (
                    "EXIT",
                    "FLATTEN",
                    0,
                    "FORCED EXIT",
                ),
                "CURRENT_POSITION_STATE": "FLAT",
                "CURRENT_POSITION_CONTRACTS": 0,
                "CURRENT_POSITION_ENTRY_SIDE": "NONE",
            },
        ),
        (
            "safety-false-live",
            {"position_reconciliation_ok": False},
            _expected_return(
                status="BLOCKED",
                reason="POSITION RECONCILIATION NOT OK",
                safety_ok=False,
                safety_reason="POSITION RECONCILIATION NOT OK",
            ),
            {},
        ),
        (
            "payload-invalid-account",
            {"broker_account_id": None},
            _expected_return(
                status="PAYLOAD_BLOCKED",
                reason="ACCOUNT ID NOT AVAILABLE",
                safety_ok=True,
                safety_reason="EXECUTION SAFETY CHECK PASSED",
            ),
            {},
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_dispatch_category_a_branches(
    case: str,
    overrides: dict[str, object],
    expected_return: dict[str, object],
    expected_state_changes: dict[str, object],
) -> None:
    runtime = _load_dispatch(**overrides)
    before = _state(runtime.namespace)

    if case == "payload-invalid-account":
        payload = runtime.namespace["build_tradestation_order_payload"]()
        assert payload == {
            "AccountID": None,
            "Symbol": SYNTHETIC_SYMBOL,
            "Quantity": "2",
            "OrderType": "MARKET",
            "TradeAction": "BUY",
            "TimeInForce": {"Duration": "DAY"},
            "Route": "Intelligent",
        }
        assert runtime.namespace["validate_tradestation_order_payload"](payload) == (
            False,
            "ACCOUNT ID NOT AVAILABLE",
        )

    result = runtime.function()
    after = _state(runtime.namespace)

    expected_after = {**before, **expected_state_changes}
    assert result == expected_return, case
    assert after == expected_after, case
    assert runtime.submit.call_count == 0
    assert runtime.transport.call_count == 0
    assert runtime.clock.call_count == 0


def test_dispatch_namespace_excludes_real_submit_definition() -> None:
    runtime = _load_dispatch()

    assert isinstance(runtime.namespace["submit_tradestation_order"], ForbiddenSubmit)
    assert runtime.namespace["submit_tradestation_order"] is runtime.submit
    assert runtime.submit.call_count == 0
    assert runtime.transport.call_count == 0


def test_forbidden_submit_detects_attempt_without_external_activity() -> None:
    sentinel = ForbiddenSubmit()

    with pytest.raises(AssertionError, match="^SUBMIT MUST NOT BE CALLED$"):
        sentinel({"synthetic": True})

    assert sentinel.call_count == 1


def test_forbidden_clock_detects_unexpected_pending_path() -> None:
    clock = ForbiddenClock()

    with pytest.raises(AssertionError, match="^PENDING CLOCK MUST NOT BE CALLED$"):
        clock.now("SYNTHETIC-TZ")

    assert clock.call_count == 1


def test_dispatch_category_a_loads_are_isolated() -> None:
    first = _load_dispatch(execution_side="BUY")
    second = _load_dispatch(execution_side="SELL")

    assert first.namespace is not second.namespace
    assert first.submit is not second.submit
    assert first.transport is not second.transport
    assert first.clock is not second.clock
    assert first.namespace["CURRENT_EXECUTION_SIDE"] == "BUY"
    assert second.namespace["CURRENT_EXECUTION_SIDE"] == "SELL"
    assert first.namespace["LAST_DISPATCH_SIGNATURE"] == INITIAL_SIGNATURE
    assert second.namespace["LAST_DISPATCH_SIGNATURE"] == INITIAL_SIGNATURE
    assert first.submit.call_count == second.submit.call_count == 0
    assert first.transport.call_count == second.transport.call_count == 0
    assert first.clock.call_count == second.clock.call_count == 0
