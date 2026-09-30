"""Differential parity for modular execution-intent construction."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.execution_intent import build_execution_intent
from tests.characterization.legacy_harness import load_build_execution_intent


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "execution_intent.py"
)


def _oracle_snapshot(namespace: dict[str, object]) -> dict[str, object]:
    return {
        "status": namespace["CURRENT_EXECUTION_STATUS"],
        "action": namespace["CURRENT_EXECUTION_ACTION"],
        "reason": namespace["CURRENT_EXECUTION_REASON"],
        "symbol": namespace["CURRENT_EXECUTION_SYMBOL"],
        "side": namespace["CURRENT_EXECUTION_SIDE"],
        "quantity": namespace["CURRENT_EXECUTION_QUANTITY"],
        "order_type": namespace["CURRENT_EXECUTION_ORDER_TYPE"],
    }


@pytest.mark.parametrize(
    ("case", "signal", "entry_permission", "exit_permission"),
    [
        ("long-mean-reversion", "LONG MEAN REVERSION", True, False),
        ("long-breakout", "LONG BREAKOUT", True, False),
        ("short-mean-reversion", "SHORT MEAN REVERSION", True, False),
        ("short-breakdown", "SHORT BREAKDOWN", True, False),
        ("exit", "FORCED EXIT", False, True),
        ("no-permissions", "LONG BREAKOUT", False, False),
        ("signal-none", "NONE", True, False),
        ("signal-unknown", "SYNTHETIC_UNKNOWN", True, False),
        ("entry-precedes-exit", "LONG BREAKOUT", True, True),
        (
            "unknown-entry-suppresses-exit",
            "SYNTHETIC_UNKNOWN",
            True,
            True,
        ),
    ],
)
def test_modular_execution_intent_matches_phase4_oracle(
    case: str,
    signal: str,
    entry_permission: bool,
    exit_permission: bool,
) -> None:
    position_size = 2
    symbol = "SYNTHETIC-ES"
    oracle = load_build_execution_intent(
        confirmed_signal=signal,
        entry_execution_permission=entry_permission,
        exit_execution_permission=exit_permission,
        position_size_contracts=position_size,
        symbol=symbol,
    )

    assert oracle.function() is None
    candidate_result = build_execution_intent(
        signal,
        entry_permission,
        exit_permission,
        position_size,
        symbol,
    )

    assert candidate_result == _oracle_snapshot(oracle.namespace), case
    assert oracle.transport.call_count == 0


def test_modular_execution_intent_public_signature_is_explicit() -> None:
    signature = inspect.signature(build_execution_intent)

    assert list(signature.parameters) == [
        "confirmed_signal",
        "entry_execution_permission",
        "exit_execution_permission",
        "position_size_contracts",
        "symbol",
    ]
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_modular_execution_intent_returns_independent_values() -> None:
    first = build_execution_intent("NONE", False, False, 2, "SYNTHETIC-ES")
    second = build_execution_intent("NONE", False, False, 2, "SYNTHETIC-ES")

    first["status"] = "SYNTHETIC_MUTATION"

    assert second["status"] == "IDLE"
    assert first is not second


def test_modular_execution_intent_is_autonomous_and_import_free() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    ] == ["build_execution_intent"]
    for forbidden_reference in (
        "spx_data_fase4_estable_final_candidato",
        "legacy_harness",
        "requests",
        "thetadata",
        "dotenv",
        "order_payload",
        "payload_validation",
        "position_validation",
        "dispatch_execution",
        "tradestation",
    ):
        assert forbidden_reference not in source.lower()
