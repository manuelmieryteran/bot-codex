"""Minimal injected transport contract for read-only broker lookups."""

from typing import Any, Protocol


class BrokerTransportError(Exception):
    """Transport failure reported by an injected broker transport."""


class BrokerResponsePort(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class BrokerTransportPort(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        timeout: int,
    ) -> BrokerResponsePort: ...
