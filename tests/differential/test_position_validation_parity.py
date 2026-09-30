"""Differential parity for modular position-state validation."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.position_validation import validate_position_state
from tests.characterization.legacy_harness import load_validate_position_state


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "position_validation.py"
)


@pytest.mark.parametrize(
    ("case", "position_state", "position_contracts", "position_entry_side"),
    [
        ("flat-valid", "FLAT", 0, "NONE"),
        ("flat-positive-contracts", "FLAT", 1, "NONE"),
        ("flat-distinct-positive-contracts", "FLAT", 3, "NONE"),
        ("flat-inconsistent-entry-side", "FLAT", 0, "BUY"),
        ("long-valid", "LONG", 1, "BUY"),
        ("long-valid-distinct-contracts", "LONG", 3, "BUY"),
        ("long-zero-contracts", "LONG", 0, "BUY"),
        ("long-negative-contracts", "LONG", -1, "BUY"),
        ("long-inconsistent-entry-side", "LONG", 1, "SELL"),
        ("short-valid", "SHORT", 1, "SELL"),
        ("short-valid-distinct-contracts", "SHORT", 3, "SELL"),
        ("short-zero-contracts", "SHORT", 0, "SELL"),
        ("short-negative-contracts", "SHORT", -1, "SELL"),
        ("short-inconsistent-entry-side", "SHORT", 1, "BUY"),
        ("unknown-state", "SYNTHETIC_UNKNOWN", 0, "NONE"),
    ],
)
def test_modular_position_validator_matches_phase4_oracle(
    case: str,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
) -> None:
    oracle = load_validate_position_state(
        position_state=position_state,
        position_contracts=position_contracts,
        position_entry_side=position_entry_side,
    ).function

    oracle_result = oracle()
    candidate_result = validate_position_state(
        position_state,
        position_contracts,
        position_entry_side,
    )

    assert candidate_result == oracle_result, case


def test_modular_position_validator_public_signature_is_explicit() -> None:
    signature = inspect.signature(validate_position_state)

    assert list(signature.parameters) == [
        "position_state",
        "position_contracts",
        "position_entry_side",
    ]
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_modular_position_validator_is_autonomous_and_import_free() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert [function.name for function in functions] == ["validate_position_state"]
    for forbidden_reference in (
        "spx_data_fase4_estable_final_candidato",
        "legacy_harness",
        "requests",
        "thetadata",
        "dotenv",
        "payload_validation",
        "dispatch_execution",
        "tradestation",
    ):
        assert forbidden_reference not in source.lower()


def test_operational_baseline_does_not_import_modular_position_validator() -> None:
    baseline_path = MODULE_PATH.parents[3] / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
    tree = ast.parse(
        baseline_path.read_text(encoding="utf-8"),
        filename=str(baseline_path),
    )
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert "bot_spx.execution.position_validation" not in imported_modules
