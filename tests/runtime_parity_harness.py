"""Fail-closed AST harness for Phase 4/Phase 5 runtime parity.

Only explicitly allowlisted function definitions are compiled.  Module imports,
assignments and ``main`` are never executed.  Every external capability is a
counting sentinel; category-B submission is replaced by a deterministic local
recorder and time is fixed.
"""

from __future__ import annotations

import ast
import hashlib
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PHASE4 = ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
PHASE5 = ROOT / "spx_data_FASE5.py"
PHASE4_SHA256 = "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023"
FIXED_TIME = "2026-01-02T10:00:00-05:00"

OBSERVABLES = (
    "CURRENT_EXECUTION_STATUS", "CURRENT_EXECUTION_ACTION",
    "CURRENT_EXECUTION_REASON", "CURRENT_EXECUTION_SIDE",
    "CURRENT_EXECUTION_QUANTITY", "CURRENT_EXECUTION_SYMBOL",
    "CURRENT_EXECUTION_ORDER_TYPE", "CURRENT_ENTRY_EXECUTION_PERMISSION",
    "CURRENT_EXIT_EXECUTION_PERMISSION", "CURRENT_POSITION_STATE",
    "CURRENT_POSITION_CONTRACTS", "CURRENT_POSITION_ENTRY_SIDE",
    "CURRENT_BROKER_ORDER_STATE", "CURRENT_BROKER_ORDER_ID",
    "CURRENT_BROKER_ORDER_STATUS", "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION",
    "CURRENT_PENDING_ORDER_ACTION", "CURRENT_PENDING_ORDER_SIDE",
    "CURRENT_PENDING_ORDER_QUANTITY", "CURRENT_PENDING_ORDER_SYMBOL",
    "CURRENT_PENDING_ORDER_SUBMITTED_AT", "LAST_DISPATCH_SIGNATURE",
    "CURRENT_POSITION_RECONCILIATION_OK",
)


class ExternalActivityError(AssertionError):
    pass


@dataclass
class ActivityLedger:
    transport: int = 0
    http: int = 0
    oauth: int = 0
    post: int = 0
    real_submit: int = 0
    digitalocean: int = 0
    token_reads: int = 0
    main: int = 0
    shadow: int = 0
    null_port: int = 0

    def forbidden(self, capability: str):
        def fail(*_args: object, **_kwargs: object) -> None:
            setattr(self, capability, getattr(self, capability) + 1)
            raise ExternalActivityError(f"FORBIDDEN EXTERNAL ACTIVITY: {capability}")
        return fail

    @property
    def total(self) -> int:
        return sum(self.__dict__.values())


@dataclass
class LocalSubmit:
    succeeds: bool
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(deepcopy(payload))
        return {
            "ok": self.succeeds,
            "status_code": 200 if self.succeeds else 503,
            "reason": "SYNTHETIC SUBMIT SUCCESS" if self.succeeds else "SYNTHETIC SUBMIT FAILURE",
            "response": {"Orders": [{"OrderID": "SYNTHETIC-ORDER-001"}]} if self.succeeds else {"synthetic": True},
        }


class _FixedInstant:
    def isoformat(self) -> str:
        return FIXED_TIME


class FixedClock:
    calls = 0

    @classmethod
    def now(cls, *_args: object, **_kwargs: object) -> _FixedInstant:
        cls.calls += 1
        return _FixedInstant()


@dataclass
class Runtime:
    namespace: dict[str, Any]
    ledger: ActivityLedger
    submit: LocalSubmit

    def snapshot(self) -> dict[str, Any]:
        return {name: deepcopy(self.namespace[name]) for name in OBSERVABLES}

    def dispatch(self) -> dict[str, Any]:
        return self.namespace["dispatch_execution"]()


def _definitions(path: Path, names: set[str]) -> list[ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in found} != names or any(n.decorator_list for n in found):
        raise RuntimeError("RUNTIME AST CONTRACT CHANGED")
    return found


def load_runtime(path: Path, overrides: dict[str, Any] | None = None, *, submit_success: bool = True) -> Runtime:
    if hashlib.sha256(PHASE4.read_bytes()).hexdigest() != PHASE4_SHA256:
        raise RuntimeError("PHASE 4 ORACLE HASH MISMATCH")
    phase5 = path == PHASE5
    names = {
        "validate_position_state", "execution_safety_check",
        "build_tradestation_order_payload", "validate_tradestation_order_payload",
        "_dispatch_execution_legacy" if phase5 else "dispatch_execution",
    }
    if phase5:
        names.add("dispatch_execution")
    ledger = ActivityLedger()
    submit = LocalSubmit(submit_success)
    values: dict[str, Any] = {
        "__builtins__": {"abs": abs, "dict": dict, "float": float, "int": int,
                         "isinstance": isinstance, "len": len, "str": str,
                         "TypeError": TypeError, "ValueError": ValueError,
                         "OverflowError": OverflowError},
        "EXECUTION_MODE": "LIVE", "LIVE_ORDER_EXECUTION_ENABLED": True,
        "ORDER_EXECUTION_ENVIRONMENT": "SIM", "SHADOW_EXECUTION_ENABLED": False,
        "CURRENT_BROKER_ACCOUNT_ID": "SYNTHETIC-ACCOUNT", "MARKET_TZ": object(),
        "datetime": FixedClock, "submit_tradestation_order": submit,
        "run_dispatch_shadow": ledger.forbidden("shadow"),
        "NullOrderSubmitPort": ledger.forbidden("null_port"),
        "tradestation_request": ledger.forbidden("transport"),
        "CURRENT_EXECUTION_STATUS": "READY", "CURRENT_EXECUTION_ACTION": "ENTRY",
        "CURRENT_EXECUTION_REASON": "SYNTHETIC INTENT", "CURRENT_EXECUTION_SIDE": "BUY",
        "CURRENT_EXECUTION_QUANTITY": 2, "CURRENT_EXECUTION_SYMBOL": "SYNTHETIC-ES",
        "CURRENT_EXECUTION_ORDER_TYPE": "MARKET",
        "CURRENT_ENTRY_EXECUTION_PERMISSION": "ALLOWED",
        "CURRENT_EXIT_EXECUTION_PERMISSION": "BLOCKED",
        "CURRENT_POSITION_STATE": "FLAT", "CURRENT_POSITION_CONTRACTS": 0,
        "CURRENT_POSITION_ENTRY_SIDE": "NONE", "CURRENT_POSITION_RECONCILIATION_OK": True,
        "CURRENT_BROKER_ORDER_STATE": "NONE", "CURRENT_BROKER_ORDER_ID": None,
        "CURRENT_BROKER_ORDER_STATUS": "NONE",
        "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION": "NONE",
        "CURRENT_PENDING_ORDER_ACTION": "NONE", "CURRENT_PENDING_ORDER_SIDE": "NONE",
        "CURRENT_PENDING_ORDER_QUANTITY": 0, "CURRENT_PENDING_ORDER_SYMBOL": None,
        "CURRENT_PENDING_ORDER_SUBMITTED_AT": None, "LAST_DISPATCH_SIGNATURE": None,
        "CURRENT_SHADOW_RESULT": None, "_LAST_LEGACY_SUBMIT_OBSERVATION": None,
    }
    values.update(overrides or {})
    module = ast.fix_missing_locations(ast.Module(body=_definitions(path, names), type_ignores=[]))
    exec(compile(module, str(path), "exec"), values)
    return Runtime(values, ledger, submit)


def paired(overrides: dict[str, Any] | None = None, *, submit_success: bool = True) -> tuple[Runtime, Runtime]:
    return (load_runtime(PHASE4, overrides, submit_success=submit_success),
            load_runtime(PHASE5, overrides, submit_success=submit_success))


def mismatch_records(scenario: str, step: int, phase4: Any, phase5: Any) -> list[dict[str, Any]]:
    """Return actionable, structured regressions rather than hiding differences."""
    records = []
    keys = sorted(set(phase4) | set(phase5)) if isinstance(phase4, dict) and isinstance(phase5, dict) else ["value"]
    for key in keys:
        left = phase4.get(key) if isinstance(phase4, dict) else phase4
        right = phase5.get(key) if isinstance(phase5, dict) else phase5
        if left != right:
            records.append({"scenario": scenario, "step": step, "field": key,
                            "phase4": left, "phase5": right, "expected": left,
                            "actual": right, "classification": "LEGACY_PARITY_REGRESSION"})
    return records
