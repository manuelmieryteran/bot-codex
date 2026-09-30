"""Caracterización de intención + posición → safety, sin dispatch ni submit."""

from __future__ import annotations

import pytest

from tests.characterization.legacy_harness import (
    load_build_execution_intent,
    load_execution_safety_check,
)


SYNTHETIC_SYMBOL = "SYNTHETIC-ES"


def _load_safety(**overrides: object):
    values: dict[str, object] = {
        "execution_mode": "LIVE",
        "live_order_execution_enabled": True,
        "position_reconciliation_ok": True,
        "execution_status": "READY",
        "execution_action": "ENTRY",
        "execution_side": "BUY",
        "execution_quantity": 2,
        "position_state": "FLAT",
        "position_contracts": 0,
        "position_entry_side": "NONE",
    }
    values.update(overrides)
    return load_execution_safety_check(**values)


@pytest.mark.parametrize(
    ("scenario", "overrides", "expected"),
    [
        (
            "dry-run-precedes-all-other-errors",
            {
                "execution_mode": "DRY_RUN",
                "live_order_execution_enabled": False,
                "position_reconciliation_ok": False,
                "execution_status": "IDLE",
                "position_state": "SYNTHETIC_UNKNOWN",
                "execution_action": "SYNTHETIC_UNKNOWN",
            },
            (False, "EXECUTION MODE IS NOT LIVE"),
        ),
        (
            "live-disabled",
            {"live_order_execution_enabled": False},
            (False, "LIVE ORDER EXECUTION DISABLED"),
        ),
        (
            "reconciliation-not-ok",
            {"position_reconciliation_ok": False},
            (False, "POSITION RECONCILIATION NOT OK"),
        ),
        (
            "status-not-ready",
            {"execution_status": "IDLE"},
            (False, "EXECUTION STATUS NOT READY"),
        ),
        (
            "flat-position-invalid",
            {"position_contracts": 1},
            (False, "FLAT POSITION WITH NONZERO CONTRACTS"),
        ),
        (
            "long-position-invalid",
            {
                "position_state": "LONG",
                "position_contracts": 0,
                "position_entry_side": "BUY",
            },
            (False, "LONG POSITION WITH INVALID CONTRACTS"),
        ),
        (
            "short-position-invalid-side",
            {
                "position_state": "SHORT",
                "position_contracts": 1,
                "position_entry_side": "BUY",
            },
            (False, "SHORT POSITION WITH INVALID ENTRY SIDE"),
        ),
        (
            "unknown-position",
            {"position_state": "SYNTHETIC_UNKNOWN"},
            (False, "UNKNOWN POSITION STATE"),
        ),
        (
            "invalid-action",
            {"execution_action": "SYNTHETIC_UNKNOWN"},
            (False, "INVALID EXECUTION ACTION"),
        ),
        (
            "invalid-entry-side",
            {"execution_side": "FLATTEN"},
            (False, "INVALID ENTRY SIDE"),
        ),
        (
            "zero-entry-quantity",
            {"execution_quantity": 0},
            (False, "INVALID ENTRY QUANTITY"),
        ),
        (
            "negative-entry-quantity",
            {"execution_quantity": -1},
            (False, "INVALID ENTRY QUANTITY"),
        ),
        (
            "valid-long-entry",
            {},
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "valid-short-entry",
            {"execution_side": "SELL"},
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "entry-while-already-long",
            {
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "valid-long-exit",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 0,
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "valid-short-exit",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 0,
                "position_state": "SHORT",
                "position_contracts": 3,
                "position_entry_side": "SELL",
            },
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "exit-while-flat",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 999,
            },
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "invalid-exit-side",
            {
                "execution_action": "EXIT",
                "execution_side": "SELL",
                "execution_quantity": 0,
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
            (False, "INVALID EXIT SIDE"),
        ),
        (
            "position-error-precedes-intent-errors",
            {
                "position_contracts": 1,
                "execution_action": "SYNTHETIC_UNKNOWN",
                "execution_side": "SYNTHETIC_UNKNOWN",
                "execution_quantity": -1,
            },
            (False, "FLAT POSITION WITH NONZERO CONTRACTS"),
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_execution_safety_check_exactly(
    scenario: str,
    overrides: dict[str, object],
    expected: tuple[bool, str],
) -> None:
    isolated = _load_safety(**overrides)

    assert isolated.function() == expected, scenario
    assert isolated.transport.call_count == 0


@pytest.mark.parametrize(
    (
        "case",
        "signal",
        "entry_permission",
        "exit_permission",
        "position_state",
        "position_contracts",
        "position_entry_side",
        "expected",
    ),
    [
        (
            "long-entry",
            "LONG MEAN REVERSION",
            True,
            False,
            "FLAT",
            0,
            "NONE",
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "short-entry",
            "SHORT BREAKDOWN",
            True,
            False,
            "FLAT",
            0,
            "NONE",
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "long-exit",
            "FORCED EXIT",
            False,
            True,
            "LONG",
            3,
            "BUY",
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "short-exit",
            "FORCED EXIT",
            False,
            True,
            "SHORT",
            3,
            "SELL",
            (True, "EXECUTION SAFETY CHECK PASSED"),
        ),
        (
            "idle",
            "NONE",
            False,
            False,
            "FLAT",
            0,
            "NONE",
            (False, "EXECUTION STATUS NOT READY"),
        ),
    ],
)
def test_execution_intent_to_safety_bridge(
    case: str,
    signal: str,
    entry_permission: bool,
    exit_permission: bool,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
    expected: tuple[bool, str],
) -> None:
    intent = load_build_execution_intent(
        confirmed_signal=signal,
        entry_execution_permission=entry_permission,
        exit_execution_permission=exit_permission,
        position_size_contracts=2,
        symbol=SYNTHETIC_SYMBOL,
    )
    assert intent.function() is None

    # Puente explícito: safety consume los globals mutados por intent, pero se
    # carga en otro namespace para conservar el aislamiento del harness.
    safety = _load_safety(
        execution_status=intent.namespace["CURRENT_EXECUTION_STATUS"],
        execution_action=intent.namespace["CURRENT_EXECUTION_ACTION"],
        execution_side=intent.namespace["CURRENT_EXECUTION_SIDE"],
        execution_quantity=intent.namespace["CURRENT_EXECUTION_QUANTITY"],
        position_state=position_state,
        position_contracts=position_contracts,
        position_entry_side=position_entry_side,
    )

    assert safety.function() == expected, case
    assert intent.transport.call_count == 0
    assert safety.transport.call_count == 0


def test_execution_safety_loads_are_isolated() -> None:
    first = _load_safety(execution_side="BUY")
    second = _load_safety(execution_side="SELL")

    assert first.namespace is not second.namespace
    assert first.transport is not second.transport
    assert first.namespace["CURRENT_EXECUTION_SIDE"] == "BUY"
    assert second.namespace["CURRENT_EXECUTION_SIDE"] == "SELL"
    assert first.transport.call_count == second.transport.call_count == 0

