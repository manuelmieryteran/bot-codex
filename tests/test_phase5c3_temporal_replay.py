"""Acceptance tests for the Phase 5C-3 controlled temporal replay."""

from __future__ import annotations

import ast
import hashlib

from tests.runtime_parity_harness import PHASE4, PHASE4_SHA256, PHASE5
from tests.temporal_replay_harness import FORCED_EXIT_TIME, replay_duration_minutes, run_replay, synthetic_session


def _literal(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.literal_eval(node.value)


def test_complete_replay_is_deterministic_and_green() -> None:
    first, second = run_replay(), run_replay()
    assert first == second
    assert first.digest == second.digest
    assert first.matrix["ticks"] == 36
    assert first.matrix["MATCH"] == 36
    for key in ("unexpected_mismatches", "unexpected_errors", "legacy_authority_violations", "state_invariant_violations", "determinism_failures", "real_submit_attempts", "external_activity"):
        assert first.matrix[key] == 0


def test_temporal_model_has_required_ticks_and_complete_market_inputs() -> None:
    session = synthetic_session()
    required = {"09:25", "09:30", "09:35", "09:40", "09:45", "10:00", "10:30", "11:00", "11:30", "12:00", "13:00", "14:00", "15:00", "15:30", "15:45", "16:00"}
    assert required <= {tick.time for tick in session}
    assert replay_duration_minutes() == 395
    assert all(tick.ask >= tick.bid and tick.trade_size > 0 and tick.call_oi > 0 and tick.put_oi > 0 for tick in session)


def test_long_short_and_forced_exit_lifecycles_are_observable() -> None:
    result = run_replay()
    events = {record.event_type: record for record in result.timeline}
    assert events["LONG_SUBMITTED"].legacy_result["status"] == "SUBMITTED"
    assert events["LONG_SUBMITTED"].state_post["CURRENT_PENDING_ORDER_ACTION"] == "ENTRY"
    assert events["LONG_FILLED"].state_post["CURRENT_POSITION_STATE"] == "LONG"
    assert events["LONG_FLAT"].state_post["CURRENT_POSITION_STATE"] == "FLAT"
    assert events["SHORT_SUBMITTED"].legacy_result["status"] == "SUBMITTED"
    assert events["SHORT_SUBMITTED"].state_post["CURRENT_PENDING_ORDER_ACTION"] == "ENTRY"
    assert events["SHORT_FILLED"].state_post["CURRENT_POSITION_STATE"] == "SHORT"
    assert events["SHORT_FLAT"].state_post["CURRENT_POSITION_STATE"] == "FLAT"
    assert events["FORCED_EXIT"].legacy_result["action"] == "EXIT"
    assert events["POST_FORCED_EXIT_FLAT"].state_post["CURRENT_POSITION_STATE"] == "FLAT"


def test_cutoff_data_quality_and_broker_fail_closed_transitions() -> None:
    result = run_replay()
    events = {record.event_type: record for record in result.timeline}
    assert events["BEFORE_FORCED_EXIT"].market["forced_exit"] is False
    assert events["FORCED_EXIT"].market["forced_exit"] is True
    assert events["ENTRY_CUTOFF"].legacy_result["action"] == "NONE"
    assert events["FLOW_BLOCKED"].market["flow_usable"] is False
    assert events["FLOW_BLOCKED"].legacy_result["action"] == "NONE"
    assert events["FLOW_RECOVERY"].market["flow_usable"] is True
    assert events["REJECTED"].state_post["CURRENT_BROKER_ORDER_STATE"] == "REJECTED"
    assert events["CANCELLED"].state_post["CURRENT_BROKER_ORDER_STATE"] == "CANCELLED"
    assert events["UNKNOWN"].state_post["CURRENT_BROKER_ORDER_STATE"] == "UNKNOWN"


def test_safety_ledger_and_runtime_defaults_remain_closed() -> None:
    result = run_replay()
    forbidden = ("tradestation", "transport", "http", "oauth", "post", "real_submit", "real_orders", "digitalocean", "token_reads", "main", "candidate_submit_attempts")
    assert all(result.ledger[key] == 0 for key in forbidden)
    assert result.ledger["legacy_fake_submits"] == 9
    assert result.ledger["shadow"] == result.ledger["null_port"] == 9
    assert _literal(PHASE5, "EXECUTION_MODE") == "DRY_RUN"
    assert _literal(PHASE5, "LIVE_ORDER_EXECUTION_ENABLED") is False
    assert _literal(PHASE5, "ORDER_EXECUTION_ENVIRONMENT") == "SIM"
    assert _literal(PHASE5, "SHADOW_EXECUTION_ENABLED") is False
    assert f"{_literal(PHASE5, 'FORCED_EXIT_HOUR'):02d}:{_literal(PHASE5, 'FORCED_EXIT_MINUTE'):02d}" == FORCED_EXIT_TIME
    assert hashlib.sha256(PHASE4.read_bytes()).hexdigest() == PHASE4_SHA256


def test_records_are_immutable_and_shadow_never_becomes_authoritative() -> None:
    result = run_replay()
    assert all(record.candidate_accepted and record.mismatch_count == 0 for record in result.timeline)
    assert all(record.shadow_outcome == "MATCH" for record in result.timeline)
    try:
        result.timeline[0].market["spot"] = 1
    except TypeError:
        pass
    else:
        raise AssertionError("replay record accepted mutation")
