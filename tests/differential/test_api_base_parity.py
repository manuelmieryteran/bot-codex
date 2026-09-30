"""Differential parity for modular TradeStation API-base selection."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.api_base import get_tradestation_api_base_url
from tests.characterization.legacy_harness import (
    load_get_tradestation_api_base_url,
)


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "api_base.py"
)
LIVE_URL = "https://synthetic-live.invalid"
SIM_URL = "https://synthetic-sim.invalid"


@pytest.mark.parametrize("environment", ["LIVE", "SIM"])
def test_modular_api_base_matches_phase4_oracle(environment: str) -> None:
    oracle = load_get_tradestation_api_base_url(
        order_execution_environment=environment,
        live_api_base_url=LIVE_URL,
        sim_api_base_url=SIM_URL,
    )

    assert get_tradestation_api_base_url(environment, LIVE_URL, SIM_URL) == (
        oracle.function()
    )
    assert oracle.transport.call_count == 0


def test_modular_api_base_matches_phase4_unknown_environment_exception() -> None:
    environment = "SYNTHETIC_UNKNOWN"
    oracle = load_get_tradestation_api_base_url(
        order_execution_environment=environment,
        live_api_base_url=LIVE_URL,
        sim_api_base_url=SIM_URL,
    )

    with pytest.raises(ValueError) as oracle_error:
        oracle.function()
    with pytest.raises(ValueError) as candidate_error:
        get_tradestation_api_base_url(environment, LIVE_URL, SIM_URL)

    assert candidate_error.value.args == oracle_error.value.args
    assert oracle.transport.call_count == 0


def test_modular_api_base_public_signature_is_explicit() -> None:
    signature = inspect.signature(get_tradestation_api_base_url)

    assert list(signature.parameters) == [
        "order_execution_environment",
        "live_api_base_url",
        "sim_api_base_url",
    ]
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_modular_api_base_is_autonomous_and_import_free() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)
    assert [
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    ] == ["get_tradestation_api_base_url"]
    for forbidden_reference in (
        "spx_data_fase4_estable_final_candidato",
        "legacy_harness",
        "requests",
        "thetadata",
        "dotenv",
        "payload_validation",
        "position_validation",
        "dispatch_execution",
        "tradestation_request",
    ):
        assert forbidden_reference not in source.lower()
