"""Differential parity for the transport-injected TradeStation lookup adapter."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from bot_spx.execution.broker_lookup import BrokerLookupPort
from bot_spx.execution.tradestation_broker_lookup import (
    TradeStationBrokerLookupAdapter,
)
from tests.characterization.legacy_harness import (
    load_primary_tradestation_account_id_with_fake_transport,
    load_tradestation_es_position_with_fake_transport,
)
from tests.fakes.broker_transport import FakeBrokerResponse, FakeBrokerTransport


ADAPTER_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bot_spx"
    / "execution"
    / "tradestation_broker_lookup.py"
)
TRANSPORT_PATH = ADAPTER_PATH.with_name("broker_transport.py")


def _outcome(call):
    try:
        return "return", call()
    except Exception as exc:
        return "exception", (type(exc).__name__, exc.args)


@pytest.mark.parametrize(
    (
        "case",
        "status",
        "text",
        "json_data",
        "invalid_json",
        "transport_error",
    ),
    [
        (
            "selects-first-active-futures-account",
            200,
            "OK",
            {
                "Accounts": [
                    {"AccountID": "IGNORED-EQUITY", "AccountType": "Equity", "Status": "Active"},
                    {"AccountID": "IGNORED-INACTIVE", "AccountType": "Futures", "Status": "Inactive"},
                    {"AccountID": "SYNTHETIC-ACCOUNT-1", "AccountType": "Futures", "Status": "Active"},
                    {"AccountID": "SYNTHETIC-ACCOUNT-2", "AccountType": "Futures", "Status": "Active"},
                ]
            },
            False,
            False,
        ),
        ("empty-account-list", 200, "OK", {"Accounts": []}, False, False),
        (
            "no-active-futures-account",
            200,
            "OK",
            {"Accounts": [{"AccountID": "SYNTHETIC", "AccountType": "Futures", "Status": "Inactive"}]},
            False,
            False,
        ),
        ("accounts-key-missing", 200, "OK", {}, False, False),
        ("non-200", 503, "SYNTHETIC ACCOUNT ERROR", {}, False, False),
        ("invalid-json", 200, "OK", {}, True, False),
        ("transport-error", 200, "OK", {}, False, True),
        ("malformed-json-shape", 200, "OK", [], False, False),
    ],
)
def test_primary_account_lookup_matches_phase4_oracle(
    case: str,
    status: int,
    text: str,
    json_data: object,
    invalid_json: bool,
    transport_error: bool,
) -> None:
    oracle = load_primary_tradestation_account_id_with_fake_transport(
        response_status=status,
        response_text=text,
        response_json=json_data,
        invalid_json=invalid_json,
        transport_error=transport_error,
    )
    transport = FakeBrokerTransport(
        FakeBrokerResponse(status, text, json_data, invalid_json),
        fail=transport_error,
    )
    adapter = TradeStationBrokerLookupAdapter(transport, "SYNTHETIC-ES")

    assert _outcome(adapter.get_primary_account_id) == _outcome(oracle.function), case
    assert transport.call_count == oracle.transport.call_count == 1
    assert transport.calls == [("GET", "/brokerage/accounts", 10)]
    method, url, kwargs = oracle.transport.calls[0]
    assert method == "GET"
    assert url == "https://synthetic-sim.invalid/brokerage/accounts"
    assert kwargs == {"timeout": 10}


@pytest.mark.parametrize(
    (
        "case",
        "account_id",
        "status",
        "text",
        "json_data",
        "invalid_json",
        "transport_error",
    ),
    [
        (
            "finds-symbol-case-insensitively",
            "SYNTHETIC-ACCOUNT",
            200,
            "OK",
            {"Positions": [{"Symbol": "OTHER", "Quantity": "9"}, {"Symbol": "synthetic-es", "Quantity": "2"}]},
            False,
            False,
        ),
        ("empty-position-list", "SYNTHETIC-ACCOUNT", 200, "OK", {"Positions": []}, False, False),
        ("positions-key-missing", "SYNTHETIC-ACCOUNT", 200, "OK", {}, False, False),
        ("account-id-missing", None, 200, "OK", {"Positions": []}, False, False),
        ("non-200", "SYNTHETIC-ACCOUNT", 500, "SYNTHETIC POSITION ERROR", {}, False, False),
        ("invalid-json", "SYNTHETIC-ACCOUNT", 200, "OK", {}, True, False),
        ("transport-error", "SYNTHETIC-ACCOUNT", 200, "OK", {}, False, True),
        ("malformed-json-shape", "SYNTHETIC-ACCOUNT", 200, "OK", [], False, False),
        ("malformed-position", "SYNTHETIC-ACCOUNT", 200, "OK", {"Positions": ["INVALID"]}, False, False),
    ],
)
def test_es_position_lookup_matches_phase4_oracle(
    case: str,
    account_id: str | None,
    status: int,
    text: str,
    json_data: object,
    invalid_json: bool,
    transport_error: bool,
) -> None:
    oracle = load_tradestation_es_position_with_fake_transport(
        response_status=status,
        response_text=text,
        response_json=json_data,
        invalid_json=invalid_json,
        transport_error=transport_error,
    )
    transport = FakeBrokerTransport(
        FakeBrokerResponse(status, text, json_data, invalid_json),
        fail=transport_error,
    )
    adapter = TradeStationBrokerLookupAdapter(transport, "SYNTHETIC-ES")

    candidate = lambda: adapter.get_es_position(account_id)
    oracle_call = lambda: oracle.function(account_id)
    assert _outcome(candidate) == _outcome(oracle_call), case
    expected_calls = 0 if not account_id else 1
    assert transport.call_count == oracle.transport.call_count == expected_calls
    if expected_calls:
        assert transport.calls == [
            ("GET", f"/brokerage/accounts/{account_id}/positions", 10)
        ]
        method, url, kwargs = oracle.transport.calls[0]
        assert method == "GET"
        assert url == (
            f"https://synthetic-sim.invalid/brokerage/accounts/{account_id}/positions"
        )
        assert kwargs == {"timeout": 10}


def test_adapter_implements_broker_lookup_port_contract() -> None:
    methods = {
        name
        for name, value in inspect.getmembers(
            TradeStationBrokerLookupAdapter,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }
    port_methods = {
        name
        for name, value in inspect.getmembers(
            BrokerLookupPort,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }

    assert methods == port_methods == {"get_primary_account_id", "get_es_position"}


@pytest.mark.parametrize("path", [ADAPTER_PATH, TRANSPORT_PATH])
def test_adapter_and_transport_contract_have_no_concrete_network_dependency(
    path: Path,
) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported_modules = {
        node.module or ""
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }

    assert "requests" not in imported_modules
    assert "httpx" not in imported_modules
    assert "urllib" not in imported_modules
    assert "dotenv" not in imported_modules
