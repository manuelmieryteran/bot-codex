"""Strict read-only HTTP transport for the TradeStation SIM API."""

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Mapping, Protocol
from urllib import error, request

from bot_spx.execution.broker_transport import BrokerTransportError


SIM_API_BASE_URL = "https://sim-api.tradestation.com/v3"
LIVE_API_BASE_URL = "https://api.tradestation.com/v3"
READ_ONLY_SCOPES = frozenset({"openid", "ReadAccount"})
ACCESS_TOKEN_ENVIRONMENT_VARIABLE = "TS_ACCESS_TOKEN"
_ACCOUNT_POSITIONS_PATH = re.compile(
    r"^/brokerage/accounts/[^/?#]+/positions$"
)


class ReadOnlyHTTPClientError(Exception):
    """Failure raised by the injected low-level GET client."""


class ReadOnlyHTTPClient(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout: int,
    ) -> "ReadOnlyHTTPResponse": ...


@dataclass(frozen=True)
class ReadOnlyHTTPResponse:
    status_code: int
    text: str

    def json(self) -> Any:
        return json.loads(self.text)


class UrllibReadOnlyHTTPClient:
    """Concrete GET-only client; it exposes no write-method API."""

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout: int,
    ) -> ReadOnlyHTTPResponse:
        http_request = request.Request(
            url,
            headers=dict(headers),
            method="GET",
        )
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return ReadOnlyHTTPResponse(response.status, body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return ReadOnlyHTTPResponse(exc.code, body)
        except (error.URLError, OSError, TimeoutError) as exc:
            raise ReadOnlyHTTPClientError(type(exc).__name__) from exc


class TradeStationSIMReadOnlyTransport:
    """SIM-only, GET-only transport implementing ``BrokerTransportPort``."""

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = SIM_API_BASE_URL,
        http_client: ReadOnlyHTTPClient | None = None,
    ) -> None:
        if base_url != SIM_API_BASE_URL:
            raise ValueError("TRADESTATION READ-ONLY TRANSPORT REQUIRES SIM BASE URL")
        if not access_token or not access_token.strip():
            raise ValueError("TRADESTATION ACCESS TOKEN NOT AVAILABLE")
        self._access_token = access_token
        self._base_url = base_url
        self._http_client = http_client or UrllibReadOnlyHTTPClient()

    @classmethod
    def from_environment(
        cls,
        *,
        environ: Mapping[str, str] | None = None,
        http_client: ReadOnlyHTTPClient | None = None,
    ) -> "TradeStationSIMReadOnlyTransport":
        environment = os.environ if environ is None else environ
        return cls(
            environment.get(ACCESS_TOKEN_ENVIRONMENT_VARIABLE, ""),
            http_client=http_client,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        timeout: int,
    ) -> ReadOnlyHTTPResponse:
        if method != "GET":
            raise ValueError("TRADESTATION READ-ONLY TRANSPORT ALLOWS GET ONLY")
        if not self.is_allowed_path(path):
            raise ValueError("TRADESTATION READ-ONLY PATH NOT ALLOWED")
        if timeout <= 0:
            raise ValueError("TRADESTATION TIMEOUT MUST BE POSITIVE")

        try:
            return self._http_client.get(
                f"{self._base_url}{path}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
                timeout=timeout,
            )
        except ReadOnlyHTTPClientError as exc:
            raise BrokerTransportError(str(exc)) from exc

    @staticmethod
    def is_allowed_path(path: str) -> bool:
        return path == "/brokerage/accounts" or bool(
            _ACCOUNT_POSITIONS_PATH.fullmatch(path)
        )

    @staticmethod
    def redact_token(token: str) -> str:
        if not token:
            return "<missing>"
        return "<redacted>"

    @staticmethod
    def redact_account_id(account_id: str | None) -> str:
        if not account_id:
            return "<missing>"
        suffix = account_id[-4:] if len(account_id) > 4 else "****"
        return f"<redacted:{suffix}>"
