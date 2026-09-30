"""Differential parity for modular execution safety checks."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.execution_safety import execution_safety_check
from tests.characterization.legacy_harness import load_execution_safety_check


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "execution_safety.py"
)
DEFAULTS: dict[str, object] = {
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


@pytest.mark.parametrize(
    ("case", "overrides"),
    [
        (
            "execution-mode-precedes-all",
            {
                "execution_mode": "DRY_RUN",
                "live_order_execution_enabled": False,
                "position_reconciliation_ok": False,
                "execution_status": "IDLE",
                "position_state": "SYNTHETIC_UNKNOWN",
                "execution_action": "SYNTHETIC_UNKNOWN",
            },
        ),
        ("live-disabled", {"live_order_execution_enabled": False}),
        ("reconciliation-not-ok", {"position_reconciliation_ok": False}),
        ("status-not-ready", {"execution_status": "IDLE"}),
        ("flat-position-invalid", {"position_contracts": 1}),
        (
            "long-position-invalid-contracts",
            {
                "position_state": "LONG",
                "position_contracts": 0,
                "position_entry_side": "BUY",
            },
        ),
        (
            "short-position-invalid-side",
            {
                "position_state": "SHORT",
                "position_contracts": 1,
                "position_entry_side": "BUY",
            },
        ),
        ("unknown-position", {"position_state": "SYNTHETIC_UNKNOWN"}),
        ("invalid-action", {"execution_action": "SYNTHETIC_UNKNOWN"}),
        ("invalid-entry-side", {"execution_side": "FLATTEN"}),
        ("zero-entry-quantity", {"execution_quantity": 0}),
        ("negative-entry-quantity", {"execution_quantity": -1}),
        ("valid-long-entry", {}),
        ("valid-short-entry", {"execution_side": "SELL"}),
        (
            "entry-while-already-long",
            {
                "position_state": "LONG",
                "position_contracts": 3,
                "position_entry_side": "BUY",
            },
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
        ),
        (
            "exit-flat-quantity-not-validated",
            {
                "execution_action": "EXIT",
                "execution_side": "FLATTEN",
                "execution_quantity": 999,
            },
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
        ),
        (
            "position-error-precedes-intent-errors",
            {
                "position_contracts": 1,
                "execution_action": "SYNTHETIC_UNKNOWN",
                "execution_side": "SYNTHETIC_UNKNOWN",
                "execution_quantity": -1,
            },
        ),
    ],
)
def test_modular_execution_safety_matches_phase4_oracle(
    case: str,
    overrides: dict[str, object],
) -> None:
    values = DEFAULTS | overrides
    oracle = load_execution_safety_check(**values)

    oracle_result = oracle.function()
    candidate_result = execution_safety_check(
        values["execution_mode"],
        values["live_order_execution_enabled"],
        values["position_reconciliation_ok"],
        values["execution_status"],
        values["execution_action"],
        values["execution_side"],
        values["execution_quantity"],
        values["position_state"],
        values["position_contracts"],
        values["position_entry_side"],
    )

    assert candidate_result == oracle_result, case
    assert oracle.transport.call_count == 0


def test_modular_execution_safety_public_signature_is_explicit() -> None:
    signature = inspect.signature(execution_safety_check)

    assert list(signature.parameters) == list(DEFAULTS)
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_modular_execution_safety_has_only_the_position_validator_dependency() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)]

    assert len(imports) == 1
    assert imports[0].module == "bot_spx.execution.position_validation"
    assert [alias.name for alias in imports[0].names] == ["validate_position_state"]
    for forbidden_reference in (
        "spx_data_fase4_estable_final_candidato",
        "legacy_harness",
        "requests",
        "thetadata",
        "dotenv",
        "order_payload",
        "payload_validation",
        "dispatch_execution",
        "tradestation",
    ):
        assert forbidden_reference not in source.lower()
