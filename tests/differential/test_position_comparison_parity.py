"""Differential parity for internal-versus-broker position comparison."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.position_comparison import (
    compare_internal_vs_broker_position,
)
from tests.characterization.legacy_harness import (
    load_compare_internal_vs_broker_position,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "position_comparison.py"
)


@pytest.mark.parametrize(
    (
        "case",
        "position_state",
        "position_contracts",
        "position_entry_side",
        "broker_position",
    ),
    [
        ("flat-match", "FLAT", 0, "NONE", None),
        ("long-match", "LONG", 3, "BUY", {"Quantity": 3}),
        ("short-match", "SHORT", 3, "SELL", {"Quantity": -3}),
        ("unknown-broker", "FLAT", 0, "NONE", {"Quantity": "ABC"}),
        ("state-mismatch", "FLAT", 0, "NONE", {"Quantity": 1}),
        ("contracts-mismatch", "LONG", 2, "BUY", {"Quantity": 3}),
        ("entry-side-mismatch", "LONG", 3, "SELL", {"Quantity": 3}),
    ],
)
def test_modular_position_comparison_matches_phase4_oracle(
    case: str,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
    broker_position: object,
) -> None:
    oracle = load_compare_internal_vs_broker_position(
        position_state=position_state,
        position_contracts=position_contracts,
        position_entry_side=position_entry_side,
    )

    candidate = compare_internal_vs_broker_position(
        position_state,
        position_contracts,
        position_entry_side,
        broker_position,
    )

    assert candidate == oracle.function(broker_position), case
    assert oracle.transport.call_count == 0


def test_modular_position_comparison_public_signature_is_explicit() -> None:
    signature = inspect.signature(compare_internal_vs_broker_position)

    assert list(signature.parameters) == [
        "position_state",
        "position_contracts",
        "position_entry_side",
        "broker_position",
    ]


def test_modular_position_comparison_only_depends_on_normalization() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]

    assert len(imports) == 1
    assert imports[0].module == "bot_spx.execution.broker_position"
    assert [alias.name for alias in imports[0].names] == [
        "normalize_tradestation_es_position"
    ]
    for forbidden_reference in (
        "requests",
        "http",
        "tradestation_request",
        "token",
        "credential",
        "dotenv",
    ):
        assert forbidden_reference not in source.lower()
