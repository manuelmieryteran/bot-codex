"""Safety contract for the concrete but unconnected SIM read-only transport."""

from __future__ import annotations

import inspect

import pytest

from bot_spx.execution.broker_transport import BrokerTransportError
from bot_spx.execution.sim_http_transport import (
    LIVE_API_BASE_URL,
    READ_ONLY_SCOPES,
    SIM_API_BASE_URL,
    ReadOnlyHTTPResponse,
    TradeStationSIMReadOnlyTransport,
    UrllibReadOnlyHTTPClient,
)
from tests.fakes.read_only_http import FakeReadOnlyHTTPClient


SYNTHETIC_TOKEN = "SYNTHETIC-ACCESS-TOKEN-DO-NOT-USE"


def _transport(response_text: str = "{}"):
    client = FakeReadOnlyHTTPClient(ReadOnlyHTTPResponse(200, response_text))
    return TradeStationSIMReadOnlyTransport(
        SYNTHETIC_TOKEN,
        http_client=client,
    ), client


def test_transport_is_locked_to_exact_sim_base_url() -> None:
    transport, client = _transport()

    transport.request("GET", "/brokerage/accounts", timeout=10)

    assert client.calls[0][0] == f"{SIM_API_BASE_URL}/brokerage/accounts"
    with pytest.raises(ValueError, match="REQUIRES SIM BASE URL"):
        TradeStationSIMReadOnlyTransport(
            SYNTHETIC_TOKEN,
            base_url=LIVE_API_BASE_URL,
            http_client=client,
        )
    with pytest.raises(ValueError, match="REQUIRES SIM BASE URL"):
        TradeStationSIMReadOnlyTransport(
            SYNTHETIC_TOKEN,
            base_url="https://synthetic.invalid/v3",
            http_client=client,
        )


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "get"])
def test_transport_rejects_every_method_except_exact_get(method: str) -> None:
    transport, client = _transport()

    with pytest.raises(ValueError, match="ALLOWS GET ONLY"):
        transport.request(method, "/brokerage/accounts", timeout=10)

    assert client.calls == []


@pytest.mark.parametrize(
    "path",
    [
        "/brokerage/accounts/SYNTHETIC/positions",
        "/brokerage/accounts/123-ABC_456/positions",
    ],
)
def test_transport_allows_only_contractual_read_paths(path: str) -> None:
    transport, client = _transport()

    transport.request("GET", path, timeout=7)

    assert client.calls == [(f"{SIM_API_BASE_URL}{path}", {
        "Accept": "application/json",
        "Authorization": f"Bearer {SYNTHETIC_TOKEN}",
    }, 7)]


@pytest.mark.parametrize(
    "path",
    [
        "/orders",
        "/brokerage/accounts/SYNTHETIC/orders",
        "/brokerage/accounts/SYNTHETIC/positions/extra",
        "/brokerage/accounts/SYNTHETIC/positions?foo=bar",
        "/brokerage/accounts//positions",
        "https://api.tradestation.com/v3/brokerage/accounts",
    ],
)
def test_transport_rejects_non_allowlisted_paths(path: str) -> None:
    transport, client = _transport()

    with pytest.raises(ValueError, match="PATH NOT ALLOWED"):
        transport.request("GET", path, timeout=10)

    assert client.calls == []


def test_transport_adds_bearer_header_without_exposing_token_in_repr() -> None:
    transport, client = _transport()

    transport.request("GET", "/brokerage/accounts", timeout=10)

    _, headers, timeout = client.calls[0]
    assert headers == {
        "Accept": "application/json",
        "Authorization": f"Bearer {SYNTHETIC_TOKEN}",
    }
    assert timeout == 10
    assert SYNTHETIC_TOKEN not in repr(transport)
    assert transport.redact_token(SYNTHETIC_TOKEN) == "<redacted>"


def test_transport_redacts_account_identifiers() -> None:
    transport, _ = _transport()

    assert transport.redact_account_id("SYNTHETIC-ACCOUNT-1234") == (
        "<redacted:1234>"
    )
    assert "SYNTHETIC-ACCOUNT" not in transport.redact_account_id(
        "SYNTHETIC-ACCOUNT-1234"
    )
    assert transport.redact_account_id(None) == "<missing>"


def test_transport_converts_low_level_errors() -> None:
    client = FakeReadOnlyHTTPClient(ReadOnlyHTTPResponse(200, "{}"), fail=True)
    transport = TradeStationSIMReadOnlyTransport(
        SYNTHETIC_TOKEN,
        http_client=client,
    )

    with pytest.raises(BrokerTransportError, match="SYNTHETIC CONNECTION FAILURE"):
        transport.request("GET", "/brokerage/accounts", timeout=10)


def test_transport_requires_external_nonempty_access_token() -> None:
    client = FakeReadOnlyHTTPClient(ReadOnlyHTTPResponse(200, "{}"))

    with pytest.raises(ValueError, match="ACCESS TOKEN NOT AVAILABLE"):
        TradeStationSIMReadOnlyTransport("", http_client=client)
    with pytest.raises(ValueError, match="ACCESS TOKEN NOT AVAILABLE"):
        TradeStationSIMReadOnlyTransport.from_environment(
            environ={},
            http_client=client,
        )


def test_read_only_scope_contract_excludes_trade_and_refresh_scope() -> None:
    assert READ_ONLY_SCOPES == {"openid", "ReadAccount"}
    assert "Trade" not in READ_ONLY_SCOPES
    assert "offline_access" not in READ_ONLY_SCOPES


def test_concrete_client_and_transport_expose_no_write_methods() -> None:
    forbidden = {"post", "put", "patch", "delete"}
    client_methods = {
        name.lower()
        for name, value in inspect.getmembers(
            UrllibReadOnlyHTTPClient,
            predicate=inspect.isfunction,
        )
    }
    transport_methods = {
        name.lower()
        for name, value in inspect.getmembers(
            TradeStationSIMReadOnlyTransport,
            predicate=inspect.isfunction,
        )
    }

    assert client_methods.isdisjoint(forbidden)
    assert transport_methods.isdisjoint(forbidden)
