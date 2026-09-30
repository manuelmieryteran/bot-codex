"""Differential parity for pure internal-versus-broker reconciliation."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.position_reconciliation import (
    reconcile_internal_with_broker_position,
)
from tests.characterization.legacy_harness import (
    load_reconcile_internal_with_broker_position,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "position_reconciliation.py"
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
        ("entry-side-mismatch", "SHORT", 3, "BUY", {"Quantity": -3}),
    ],
)
def test_modular_position_reconciliation_matches_phase4_oracle(
    case: str,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
    broker_position: object,
) -> None:
    oracle = load_reconcile_internal_with_broker_position(
        position_state=position_state,
        position_contracts=position_contracts,
        position_entry_side=position_entry_side,
    )

    candidate = reconcile_internal_with_broker_position(
        position_state,
        position_contracts,
        position_entry_side,
        broker_position,
    )

    assert candidate == oracle.function(broker_position), case
    assert oracle.transport.call_count == 0


def test_modular_position_reconciliation_public_signature_is_explicit() -> None:
    signature = inspect.signature(reconcile_internal_with_broker_position)

    assert list(signature.parameters) == [
        "position_state",
        "position_contracts",
        "position_entry_side",
        "broker_position",
    ]


def test_modular_reconciliation_only_depends_on_dataclasses_and_comparison() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]

    assert {node.module for node in imports} == {
        "dataclasses",
        "bot_spx.execution.position_comparison",
    }
    for forbidden_reference in (
        "requests",
        "http",
        "tradestation_request",
        "get_tradestation_es_position",
        "token",
        "credential",
        "dotenv",
    ):
        assert forbidden_reference not in source.lower()
