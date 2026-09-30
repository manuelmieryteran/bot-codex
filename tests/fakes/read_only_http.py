"""Low-level GET client fake for the strict SIM transport."""

from collections.abc import Mapping

from bot_spx.execution.sim_http_transport import (
    ReadOnlyHTTPClientError,
    ReadOnlyHTTPResponse,
)


class FakeReadOnlyHTTPClient:
    def __init__(
        self,
        response: ReadOnlyHTTPResponse,
        *,
        fail: bool = False,
    ) -> None:
        self.response = response
        self.fail = fail
        self.calls: list[tuple[str, dict[str, str], int]] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout: int,
    ) -> ReadOnlyHTTPResponse:
        self.calls.append((url, dict(headers), timeout))
        if self.fail:
            raise ReadOnlyHTTPClientError("SYNTHETIC CONNECTION FAILURE")
        return self.response
