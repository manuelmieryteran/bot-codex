"""Differential parity for modular TradeStation payload construction."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.order_payload import build_tradestation_order_payload
from bot_spx.execution.payload_validation import validate_tradestation_order_payload
from tests.characterization.legacy_harness import (
    load_build_tradestation_order_payload,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "order_payload.py"
)


@pytest.mark.parametrize(
    (
        "case",
        "execution_action",
        "execution_side",
        "execution_quantity",
        "position_state",
        "position_contracts",
        "is_valid",
    ),
    [
        ("entry-buy", "ENTRY", "BUY", 2, "FLAT", 0, True),
        ("entry-sell", "ENTRY", "SELL", 2, "FLAT", 0, True),
        ("exit-long", "EXIT", "FLATTEN", 0, "LONG", 3, True),
        ("exit-short", "EXIT", "FLATTEN", 0, "SHORT", 3, True),
        ("unsupported-action", "SYNTHETIC_UNKNOWN", "BUY", 2, "FLAT", 0, False),
    ],
)
def test_modular_order_payload_matches_phase4_oracle(
    case: str,
    execution_action: str,
    execution_side: str,
    execution_quantity: int,
    position_state: str,
    position_contracts: int,
    is_valid: bool,
) -> None:
    account_id = "SYNTHETIC-ACCOUNT"
    symbol = "SYNTHETIC-ES"
    order_type = "MARKET"
    oracle_runtime = load_build_tradestation_order_payload(
        execution_action=execution_action,
        execution_side=execution_side,
        execution_quantity=execution_quantity,
        position_state=position_state,
        position_contracts=position_contracts,
        account_id=account_id,
        symbol=symbol,
        order_type=order_type,
    )

    oracle_payload = oracle_runtime.function()
    candidate_payload = build_tradestation_order_payload(
        execution_action,
        execution_side,
        execution_quantity,
        account_id,
        symbol,
        order_type,
        position_state,
        position_contracts,
    )

    assert candidate_payload == oracle_payload, case
    assert oracle_runtime.transport.call_count == 0
    assert validate_tradestation_order_payload(candidate_payload) == (
        (True, "ORDER PAYLOAD VALID")
        if is_valid
        else (False, "ORDER PAYLOAD IS NONE")
    )
    assert oracle_runtime.namespace["validate_tradestation_order_payload"](
        oracle_payload
    ) == validate_tradestation_order_payload(candidate_payload)


def test_modular_order_payload_public_signature_is_explicit() -> None:
    signature = inspect.signature(build_tradestation_order_payload)

    assert list(signature.parameters) == [
        "execution_action",
        "execution_side",
        "execution_quantity",
        "account_id",
        "symbol",
        "order_type",
        "position_state",
        "position_contracts",
    ]
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_modular_order_payload_is_autonomous_and_import_free() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    ] == ["build_tradestation_order_payload"]
    for forbidden_reference in (
        "spx_data_fase4_estable_final_candidato",
        "legacy_harness",
        "requests",
        "thetadata",
        "dotenv",
        "payload_validation",
        "dispatch_execution",
        "tradestation_request",
    ):
        assert forbidden_reference not in source.lower()
