"""Differential parity for broker-position normalization."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.broker_position import normalize_tradestation_es_position
from tests.characterization.legacy_harness import (
    load_normalize_tradestation_es_position,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "broker_position.py"
)


@pytest.mark.parametrize(
    ("case", "position"),
    [
        ("none", None),
        ("empty", {}),
        ("missing-quantity", {"Symbol": "SYNTHETIC-ES"}),
        ("zero", {"Quantity": 0}),
        ("positive-int", {"Quantity": 3}),
        ("negative-int", {"Quantity": -3}),
        ("positive-string", {"Quantity": "2"}),
        ("negative-string", {"Quantity": "-2"}),
        ("positive-decimal-truncates", {"Quantity": "2.9"}),
        ("negative-decimal-truncates", {"Quantity": "-2.9"}),
        ("boolean-legacy", {"Quantity": True}),
        ("invalid-string", {"Quantity": "ABC"}),
        ("invalid-type", {"Quantity": object()}),
    ],
)
def test_modular_normalization_matches_phase4_oracle(
    case: str,
    position: object,
) -> None:
    oracle = load_normalize_tradestation_es_position()

    assert normalize_tradestation_es_position(position) == oracle.function(position), case
    assert oracle.transport.call_count == 0


def test_modular_normalization_public_signature_is_compatible() -> None:
    signature = inspect.signature(normalize_tradestation_es_position)

    assert list(signature.parameters) == ["position"]
    assert signature.parameters["position"].default is inspect.Parameter.empty


def test_modular_normalization_is_autonomous_and_import_free() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    ] == ["normalize_tradestation_es_position"]
    for forbidden_reference in (
        "requests",
        "http",
        "tradestation_request",
        "token",
        "credential",
        "dotenv",
    ):
        assert forbidden_reference not in source.lower()
