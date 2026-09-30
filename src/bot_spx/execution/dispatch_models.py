"""Minimal explicit models for pure execution-dispatch transitions."""

from dataclasses import dataclass
from typing import Any


DispatchSignature = tuple[str, str, int, str]


@dataclass(frozen=True)
class ExecutionState:
    broker_account_id: str | None
    broker_position_available: bool
    broker_position_reason: str
    position_reconciliation_ok: bool
    position_reconciliation_action: str
    position_reconciliation_reason: str
    broker_order_state: str
    broker_order_id: str | None
    broker_order_status: str
    broker_order_status_description: str
    dispatch_status: str
    dispatch_reason: str
    dispatch_id: str | None
    position_state: str
    position_contracts: int
    position_entry_side: str
    last_dispatch_signature: DispatchSignature | None
    pending_order_action: str
    pending_order_side: str
    pending_order_quantity: int
    pending_order_symbol: str | None
    pending_order_submitted_at: str | None


@dataclass(frozen=True)
class ExecutionIntent:
    status: str
    action: str
    side: str
    quantity: int
    symbol: str
    order_type: str
    reason: str


@dataclass(frozen=True)
class DispatchConfig:
    execution_mode: str
    live_order_execution_enabled: bool
    position_reconciliation_ok: bool
    broker_account_id: str | None
    submission_timestamp: str | None


@dataclass(frozen=True)
class DispatchEffect:
    kind: str
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class DispatchTransition:
    state: ExecutionState
    effect: DispatchEffect
    result: dict[str, Any]
