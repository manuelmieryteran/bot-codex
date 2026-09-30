"""Deterministic broker transport fake with no networking capability."""

from dataclasses import dataclass
from typing import Any

from bot_spx.execution.broker_transport import BrokerTransportError


class SyntheticRequestException(BrokerTransportError):
    """Synthetic failure whose name matches the isolated legacy fake."""


@dataclass(frozen=True)
class FakeBrokerResponse:
    status_code: int
    text: str
    json_data: Any
    invalid_json: bool = False

    def json(self) -> Any:
        if self.invalid_json:
            raise ValueError("SYNTHETIC INVALID JSON")
        return self.json_data


class FakeBrokerTransport:
    def __init__(self, response: FakeBrokerResponse, fail: bool = False) -> None:
        self.response = response
        self.fail = fail
        self.call_count = 0
        self.calls: list[tuple[str, str, int]] = []

    def request(self, method: str, path: str, *, timeout: int) -> FakeBrokerResponse:
        self.call_count += 1
        self.calls.append((method, path, timeout))
        if self.fail:
            raise SyntheticRequestException("SYNTHETIC TRANSPORT FAILURE")
        return self.response
