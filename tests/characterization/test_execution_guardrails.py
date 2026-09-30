"""Caracterización dinámica y sin red de los primeros guardrails de ejecución."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.characterization.legacy_harness import (
    BASELINE_PATH,
    NETWORK_SENTINEL_MESSAGE,
    ForbiddenTransport,
    load_submit_tradestation_order,
)


SYNTHETIC_VALID_PAYLOAD = {
    "AccountID": "SYNTHETIC-ACCOUNT",
    "Symbol": "SYNTHETIC-ES",
    "Quantity": "1",
    "OrderType": "MARKET",
    "TradeAction": "BUY",
    "TimeInForce": {"Duration": "DAY"},
    "Route": "Intelligent",
}


def _literal_assignment(path: Path, name: str) -> object:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(statement.value)
    pytest.fail(f"No se encontró la asignación {name}")


def test_live_disabled_blocks_before_transport() -> None:
    isolated = load_submit_tradestation_order(
        live_order_execution_enabled=False,
        order_execution_environment="SIM",
    )

    result = isolated.function(SYNTHETIC_VALID_PAYLOAD)

    assert result == {
        "ok": False,
        "status_code": None,
        "reason": "LIVE ORDER EXECUTION DISABLED",
        "response": None,
    }
    assert isolated.transport.call_count == 0


def test_non_sim_environment_blocks_before_transport() -> None:
    isolated = load_submit_tradestation_order(
        live_order_execution_enabled=True,
        order_execution_environment="SYNTHETIC_NON_SIM",
    )

    result = isolated.function(SYNTHETIC_VALID_PAYLOAD)

    assert result == {
        "ok": False,
        "status_code": None,
        "reason": "ORDER EXECUTION ENVIRONMENT NOT SIM",
        "response": None,
    }
    assert isolated.transport.call_count == 0


def test_forbidden_transport_sentinel_detects_an_attempt_without_network() -> None:
    sentinel = ForbiddenTransport()

    with pytest.raises(AssertionError, match=NETWORK_SENTINEL_MESSAGE):
        sentinel("POST", "https://invalid.test/synthetic")

    assert sentinel.call_count == 1


def test_isolated_override_does_not_change_baseline_or_another_namespace() -> None:
    overridden = load_submit_tradestation_order(
        live_order_execution_enabled=True,
        order_execution_environment="SYNTHETIC_NON_SIM",
    )
    clean = load_submit_tradestation_order()

    assert overridden.namespace["LIVE_ORDER_EXECUTION_ENABLED"] is True
    assert clean.namespace["LIVE_ORDER_EXECUTION_ENABLED"] is False
    assert overridden.namespace is not clean.namespace
    assert overridden.transport is not clean.transport
    assert _literal_assignment(BASELINE_PATH, "LIVE_ORDER_EXECUTION_ENABLED") is False

