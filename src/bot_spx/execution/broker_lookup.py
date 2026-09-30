"""Minimal broker lookup port required by reconciliation orchestration."""

from typing import Any, Protocol


class BrokerLookupPort(Protocol):
    def get_primary_account_id(self) -> tuple[str | None, str]: ...

    def get_es_position(self, account_id: str) -> dict[str, Any]: ...
