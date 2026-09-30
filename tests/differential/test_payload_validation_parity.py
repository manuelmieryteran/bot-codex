"""Differential parity for the first Phase 5B modular extraction."""

from __future__ import annotations

import ast
from copy import deepcopy
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.payload_validation import (
    validate_tradestation_order_payload,
)
from tests.characterization.legacy_harness import (
    load_validate_tradestation_order_payload,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "payload_validation.py"
)
VALID_PAYLOAD = {
    "AccountID": "SYNTHETIC-ACCOUNT",
    "Symbol": "SYNTHETIC-ES",
    "Quantity": "1",
    "OrderType": "MARKET",
    "TradeAction": "BUY",
    "TimeInForce": {"Duration": "DAY"},
    "Route": "Intelligent",
}


def _payload_with(**changes: object) -> dict[str, object]:
    payload = deepcopy(VALID_PAYLOAD)
    payload.update(changes)
    return payload


def _without(field: str) -> dict[str, object]:
    return {key: value for key, value in VALID_PAYLOAD.items() if key != field}


@pytest.mark.parametrize(
    ("case", "payload"),
    [
        ("valid", VALID_PAYLOAD),
        ("none", None),
        ("non-dict-empty-list", []),
        ("account-none", _payload_with(AccountID=None)),
        ("account-missing", _without("AccountID")),
        ("symbol-empty", _payload_with(Symbol="")),
        ("symbol-missing", _without("Symbol")),
        ("quantity-zero", _payload_with(Quantity="0")),
        ("quantity-nonnumeric", _payload_with(Quantity="ABC")),
        ("quantity-negative", _payload_with(Quantity="-1")),
        ("quantity-decimal-string", _payload_with(Quantity="1.5")),
        ("quantity-bool-legacy", _payload_with(Quantity=True)),
        ("trade-action-invalid", _payload_with(TradeAction="HOLD")),
        ("order-type-invalid", _payload_with(OrderType="LIMIT")),
        ("time-in-force-not-dict", _payload_with(TimeInForce="DAY")),
        ("duration-invalid", _payload_with(TimeInForce={"Duration": "GTC"})),
        ("duration-missing", _payload_with(TimeInForce={})),
        ("route-invalid", _payload_with(Route="SyntheticRoute")),
        ("quantity-missing", _without("Quantity")),
        ("order-type-missing", _without("OrderType")),
        ("trade-action-missing", _without("TradeAction")),
        ("time-in-force-missing", _without("TimeInForce")),
        ("route-missing", _without("Route")),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_modular_validator_matches_phase4_oracle_without_mutation(
    case: str,
    payload: object,
) -> None:
    oracle = load_validate_tradestation_order_payload().function
    oracle_input = deepcopy(payload)
    candidate_input = deepcopy(payload)
    oracle_before = deepcopy(oracle_input)
    candidate_before = deepcopy(candidate_input)

    oracle_result = oracle(oracle_input)
    candidate_result = validate_tradestation_order_payload(candidate_input)

    assert candidate_result == oracle_result, case
    assert oracle_input == oracle_before, case
    assert candidate_input == candidate_before, case


def test_modular_validator_public_signature_is_compatible() -> None:
    signature = inspect.signature(validate_tradestation_order_payload)

    assert list(signature.parameters) == ["payload"]
    assert signature.parameters["payload"].default is inspect.Parameter.empty


def test_modular_validator_is_autonomous_and_import_free() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
    functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef)
    ]

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert [function.name for function in functions] == [
        "validate_tradestation_order_payload"
    ]
    assert "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO" not in MODULE_PATH.read_text(
        encoding="utf-8"
    )
    assert "legacy_harness" not in MODULE_PATH.read_text(encoding="utf-8")
    assert "requests" not in MODULE_PATH.read_text(encoding="utf-8")
    assert "thetadata" not in MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "dotenv" not in MODULE_PATH.read_text(encoding="utf-8").lower()
