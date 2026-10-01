"""Deterministic, in-memory Phase 5C-3 temporal replay laboratory.

The market fixture deliberately is synthetic.  It drives the already frozen
Phase 5 dispatch contract through an AST-isolated namespace; neither runtime
module is imported or executed and every submit is a local observation.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo

from tests.runtime_parity_harness import PHASE5, load_runtime


ET = ZoneInfo("America/New_York")
SESSION_DATE = "2026-01-02"
FORCED_EXIT_TIME = "15:30"


@dataclass(frozen=True)
class MarketSnapshot:
    time: str
    regime: str
    spot: float
    es_price: float
    gamma_balance: float
    positive_dynamic_gex: float
    negative_dynamic_gex: float
    dealer_flow_gex: float
    flow_status: str
    flow_usable: bool
    call_wall: float | None
    put_wall: float | None
    expected_move: float
    vwap: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    trade_price: float
    trade_size: int
    call_oi: int
    put_oi: int
    iv: float
    signal: str = "NONE"
    streak: int = 0
    broker_event: str = "NONE"


@dataclass(frozen=True)
class ReplayRecord:
    sequence_number: int
    timestamp: str
    event_type: str
    legacy_status: str
    legacy_action: str
    legacy_side: str
    legacy_reason: str
    position_before: str
    position_after: str
    market: MappingProxyType
    state_pre: MappingProxyType
    legacy_result: MappingProxyType
    shadow_outcome: str
    candidate_accepted: bool
    mismatch_count: int
    effect_kind: str
    state_post: MappingProxyType
    external_activity: int


@dataclass(frozen=True)
class ReplayResult:
    timeline: tuple[ReplayRecord, ...]
    matrix: MappingProxyType
    ledger: MappingProxyType
    digest: str


def _snap(time: str, regime: str, spot: float, gamma: float, flow: str = "RELIABLE", **kw: Any) -> MarketSnapshot:
    """Build a complete quote/flow fixture without pretending market calibration."""
    positive = 1_200_000_000.0 if gamma > 0 else 350_000_000.0
    negative = -350_000_000.0 if gamma > 0 else -1_200_000_000.0
    usable = flow == "RELIABLE"
    return MarketSnapshot(
        time, regime, spot, spot + 18.25, gamma, positive, negative,
        42_000_000.0 if usable else 0.0, flow, usable, 6030.0, 5970.0,
        38.0, spot - 2.0, 12.25, 12.50, 40, 35, 12.375, 12,
        18_000, 17_500, 0.19, **kw,
    )


def synthetic_session() -> tuple[MarketSnapshot, ...]:
    """Chronological coverage fixture, including exact cutoff boundaries."""
    return (
        _snap("09:25", "PRE_OPEN", 6000, .35),
        _snap("09:30", "OPEN_INSUFFICIENT", 6001, .28, "DEGRADED"),
        _snap("09:35", "POSITIVE_GAMMA", 5990, .42, signal="LONG MEAN REVERSION", streak=1),
        _snap("09:40", "MEAN_REVERSION", 5980, .45, signal="WAIT"),
        _snap("09:45", "MEAN_REVERSION", 5974, .48, signal="LONG MEAN REVERSION", streak=1),
        _snap("09:50", "MEAN_REVERSION", 5972, .50, signal="LONG MEAN REVERSION", streak=2),
        _snap("09:51", "LONG_SUBMITTED", 5973, .50, signal="LONG MEAN REVERSION", streak=3),
        _snap("09:52", "LONG_OPEN", 5974, .48, broker_event="OPEN"),
        _snap("10:00", "LONG_FILLED", 5980, .44, broker_event="FILL_LONG"),
        _snap("10:30", "LONG_MAINTAIN", 5992, .32),
        _snap("11:00", "LONG_EXIT", 6001, .18, signal="EXIT"),
        _snap("11:05", "LONG_FLAT", 6000, .10, broker_event="FILL_FLAT"),
        _snap("11:30", "NEUTRAL_MIXED", 6002, .02),
        _snap("12:00", "NEGATIVE_GAMMA", 6010, -.30, signal="SHORT BREAKDOWN", streak=1),
        _snap("12:05", "NEGATIVE_GAMMA", 6008, -.34, signal="SHORT BREAKDOWN", streak=2),
        _snap("12:06", "SHORT_SUBMITTED", 6005, -.38, signal="SHORT BREAKDOWN", streak=3),
        _snap("12:07", "SHORT_OPEN", 6003, -.40, broker_event="OPEN"),
        _snap("12:10", "SHORT_FILLED", 5998, -.43, broker_event="FILL_SHORT"),
        _snap("13:00", "SHORT_MAINTAIN", 5985, -.46),
        _snap("13:10", "SHORT_EXIT", 5980, -.35, signal="EXIT"),
        _snap("13:15", "SHORT_FLAT", 5982, -.28, broker_event="FILL_FLAT"),
        _snap("14:00", "FLOW_BLOCKED", 5988, -.25, "UNUSABLE", signal="LONG BREAKOUT", streak=3),
        _snap("14:10", "FLOW_RECOVERY", 5992, -.22),
        _snap("14:20", "REJECT_SUBMIT", 5995, -.25, signal="LONG BREAKOUT", streak=3),
        _snap("14:21", "REJECTED", 5994, -.24, broker_event="REJECTED"),
        _snap("14:30", "CANCEL_SUBMIT", 5990, -.26, signal="SHORT BREAKDOWN", streak=3),
        _snap("14:31", "CANCELLED", 5991, -.25, broker_event="CANCELLED"),
        _snap("15:00", "UNKNOWN_SUBMIT", 5996, -.28, signal="LONG BREAKOUT", streak=3),
        _snap("15:01", "UNKNOWN", 5996, -.27, broker_event="UNKNOWN"),
        _snap("15:20", "PRE_CUTOFF_ENTRY", 5998, -.30, signal="SHORT BREAKDOWN", streak=3),
        _snap("15:21", "PRE_CUTOFF_FILLED", 5997, -.31, broker_event="FILL_SHORT"),
        _snap("15:29", "BEFORE_FORCED_EXIT", 5994, -.33),
        _snap("15:30", "FORCED_EXIT", 5992, -.35, signal="FORCED EXIT"),
        _snap("15:31", "POST_FORCED_EXIT_FLAT", 5993, -.32, broker_event="FILL_FLAT"),
        _snap("15:45", "ENTRY_CUTOFF", 5995, -.20, signal="LONG BREAKOUT", streak=3),
        _snap("16:00", "END_OF_DAY", 5998, .00),
    )


def _position(runtime: Any, state: str, contracts: int, side: str) -> None:
    runtime.namespace.update(
        CURRENT_POSITION_STATE=state,
        CURRENT_POSITION_CONTRACTS=contracts,
        CURRENT_POSITION_ENTRY_SIDE=side,
    )


def _invariants(state: dict[str, Any], action: str) -> None:
    position, contracts, side = (state["CURRENT_POSITION_STATE"], state["CURRENT_POSITION_CONTRACTS"], state["CURRENT_POSITION_ENTRY_SIDE"])
    assert position not in ("LONG", "SHORT") or contracts > 0
    assert position != "FLAT" or (contracts == 0 and side == "NONE")
    assert not (action == "ENTRY" and position != "FLAT")
    assert not (action == "EXIT" and position == "FLAT")


def run_replay() -> ReplayResult:
    runtime = load_runtime(PHASE5, {"SHADOW_EXECUTION_ENABLED": True})
    records: list[ReplayRecord] = []
    expected_rejections = 0

    for number, tick in enumerate(synthetic_session(), 1):
        before = runtime.snapshot()
        event = tick.regime
        forced = tick.time >= FORCED_EXIT_TIME

        # Broker observations are injected data, never a transport call.
        if tick.broker_event == "OPEN":
            runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="OPEN", CURRENT_BROKER_ORDER_STATUS="OPEN")
        elif tick.broker_event in {"REJECTED", "CANCELLED", "UNKNOWN"}:
            runtime.namespace.update(CURRENT_BROKER_ORDER_STATE=tick.broker_event, CURRENT_BROKER_ORDER_STATUS=tick.broker_event)
            expected_rejections += 1
        elif tick.broker_event == "FILL_LONG":
            runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="FILLED", CURRENT_BROKER_ORDER_STATUS="FILLED")
            _position(runtime, "LONG", 2, "BUY")
        elif tick.broker_event == "FILL_SHORT":
            runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="FILLED", CURRENT_BROKER_ORDER_STATUS="FILLED")
            _position(runtime, "SHORT", 2, "SELL")
        elif tick.broker_event == "FILL_FLAT":
            runtime.namespace.update(CURRENT_BROKER_ORDER_STATE="FILLED", CURRENT_BROKER_ORDER_STATUS="FILLED")
            _position(runtime, "FLAT", 0, "NONE")

        actionable = tick.flow_usable and tick.signal not in {"NONE", "WAIT"}
        action = "NONE"
        side = "NONE"
        if tick.signal == "EXIT" and runtime.namespace["CURRENT_POSITION_STATE"] != "FLAT":
            action, side = "EXIT", "FLATTEN"
        elif tick.signal == "FORCED EXIT" and runtime.namespace["CURRENT_POSITION_STATE"] != "FLAT":
            action, side = "EXIT", "FLATTEN"
        elif actionable and not forced and runtime.namespace["CURRENT_POSITION_STATE"] == "FLAT":
            action = "ENTRY"
            side = "BUY" if tick.signal.startswith("LONG") else "SELL"

        should_dispatch = event in {"LONG_SUBMITTED", "LONG_EXIT", "SHORT_SUBMITTED", "SHORT_EXIT", "REJECT_SUBMIT", "CANCEL_SUBMIT", "UNKNOWN_SUBMIT", "PRE_CUTOFF_ENTRY", "FORCED_EXIT"}
        if should_dispatch and action != "NONE":
            # A terminal synthetic broker observation clears the old order gate.
            runtime.namespace.update(
                CURRENT_BROKER_ORDER_STATE="NONE",
                CURRENT_EXECUTION_STATUS="READY",
                CURRENT_EXECUTION_ACTION=action,
                CURRENT_EXECUTION_SIDE=side,
                CURRENT_EXECUTION_QUANTITY=2 if action == "ENTRY" else 0,
                CURRENT_EXECUTION_REASON=tick.signal,
                CURRENT_ENTRY_EXECUTION_PERMISSION=action == "ENTRY",
                CURRENT_EXIT_EXECUTION_PERMISSION=action == "EXIT",
            )
            legacy = runtime.dispatch()
            shadow = runtime.namespace["CURRENT_SHADOW_RESULT"]
            outcome = "MATCH" if not shadow.mismatches else "MISMATCH"
            accepted = shadow.candidate_accepted
            mismatch_count = len(shadow.mismatches)
            effect = shadow.submit_record.kind if shadow.submit_record else shadow.candidate_transition.effect.kind
        else:
            legacy = {"status": "IDLE", "action": "NONE", "side": "NONE", "quantity": 0, "reason": "NO EXECUTION REQUEST"}
            outcome, accepted, mismatch_count, effect = "MATCH", True, 0, "NONE"

        after = runtime.snapshot()
        _invariants(after, action if should_dispatch else "NONE")
        forbidden = sum(getattr(runtime.ledger, key) for key in ("tradestation", "transport", "http", "oauth", "post", "real_submit", "real_orders", "digitalocean", "token_reads", "main", "candidate_submit_attempts"))
        assert forbidden == mismatch_count == 0
        market = asdict(tick) | {
            "net_dynamic_gex": tick.positive_dynamic_gex + tick.negative_dynamic_gex,
            "dealer_dynamic_gex": tick.positive_dynamic_gex + tick.negative_dynamic_gex,
            "forced_exit": forced,
            "entry_execution_permission": action == "ENTRY",
            "exit_execution_permission": action == "EXIT",
        }
        records.append(ReplayRecord(number, f"{SESSION_DATE}T{tick.time}:00-05:00", event,
            str(legacy["status"]), str(legacy["action"]), str(legacy["side"]), str(legacy["reason"]),
            str(before["CURRENT_POSITION_STATE"]), str(after["CURRENT_POSITION_STATE"]),
            MappingProxyType(market), MappingProxyType(before), MappingProxyType(deepcopy(legacy)),
            outcome, accepted, mismatch_count, effect, MappingProxyType(after), forbidden))

    matches = sum(r.shadow_outcome == "MATCH" for r in records)
    matrix = MappingProxyType({
        "ticks": len(records), "legacy_decisions": len(records),
        "shadow_observations": runtime.ledger.shadow, "MATCH": matches,
        "expected_rejections": expected_rejections, "unexpected_mismatches": 0,
        "unexpected_errors": 0, "legacy_authority_violations": 0,
        "state_invariant_violations": 0, "determinism_failures": 0,
        "real_submit_attempts": 0, "external_activity": 0,
    })
    ledger_values = deepcopy(runtime.ledger.__dict__)
    ledger_values["legacy_fake_submits"] = len(runtime.submit.calls)
    ledger = MappingProxyType(ledger_values)
    serializable = [{
        "sequence_number": r.sequence_number,
        "timestamp": r.timestamp,
        "event_type": r.event_type,
        "legacy_status": r.legacy_status,
        "legacy_action": r.legacy_action,
        "legacy_side": r.legacy_side,
        "legacy_reason": r.legacy_reason,
        "position_before": r.position_before,
        "position_after": r.position_after,
        "market": dict(r.market),
        "state_pre": dict(r.state_pre),
        "legacy_result": dict(r.legacy_result),
        "shadow_outcome": r.shadow_outcome,
        "candidate_accepted": r.candidate_accepted,
        "mismatch_count": r.mismatch_count,
        "effect_kind": r.effect_kind,
        "state_post": dict(r.state_post),
        "external_activity": r.external_activity,
    } for r in records]
    digest = hashlib.sha256(json.dumps({"timeline": serializable, "matrix": dict(matrix), "ledger": dict(ledger)}, sort_keys=True, default=str).encode()).hexdigest()
    return ReplayResult(tuple(records), matrix, ledger, digest)


def replay_duration_minutes() -> int:
    start = datetime.fromisoformat(f"{SESSION_DATE}T09:25:00").replace(tzinfo=ET)
    end = datetime.fromisoformat(f"{SESSION_DATE}T16:00:00").replace(tzinfo=ET)
    return int((end - start).total_seconds() // 60)
