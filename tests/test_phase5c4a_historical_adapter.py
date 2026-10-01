"""Offline acceptance and deliberate anti-lookahead attacks for Phase 5C-4A."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from bot_spx.historical import (
    DataQuality,
    HistoricalBrokerObservation,
    HistoricalContractError,
    HistoricalDatasetAdapter,
    HistoricalDerivedValue,
    HistoricalLookaheadError,
    HistoricalMarketObservation,
    HistoricalOptionsObservation,
    HistoricalReplayInput,
    Provenance,
    TemporalFirewall,
)
from tests.temporal_replay_harness import run_replay


ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 1, 2, 10, 5, tzinfo=ET)


def provenance(at: datetime = NOW) -> Provenance:
    return Provenance("synthetic-fixture", at, at, "raw", ("fixture-row",))


def market(at: datetime = NOW, *, available: datetime | None = None, seq: int = 1,
           identifier: str = "m1", kind: str = "tick", values=None, **bar):
    available = available or at
    return HistoricalMarketObservation(identifier, at, available, at, seq, kind,
                                       values or {"spot": 6000.0}, provenance(available), **bar)


def option(kind="quote", *, available=NOW, seq=2, identifier="o1", **extra):
    values = {"bid": 12.25, "ask": 12.5} if kind == "quote" else {"price": 12.375, "size": 2}
    return HistoricalOptionsObservation(identifier, NOW, available, NOW, seq, kind,
                                        values, provenance(available), **extra)


def broker(*, available=NOW, kind="state", seq=3):
    return HistoricalBrokerObservation("b1", NOW, available, NOW, seq, kind,
                                       {"status": "OPEN"}, provenance(available))


@pytest.mark.parametrize("delta,allowed", [
    (timedelta(microseconds=-1), True), (timedelta(0), True),
    (timedelta(microseconds=1), False),
])
def test_available_time_boundary(delta, allowed) -> None:
    firewall = TemporalFirewall(NOW)
    if allowed:
        assert firewall.admit(market(available=NOW + delta)) is DataQuality.VALID
    else:
        with pytest.raises(HistoricalLookaheadError):
            firewall.admit(market(available=NOW + delta))


def test_future_market_tick_rejected() -> None:
    with pytest.raises(HistoricalLookaheadError):
        TemporalFirewall(NOW).admit(market(NOW + timedelta(seconds=1), available=NOW))


@pytest.mark.parametrize("kind", ["quote", "trade"])
def test_future_option_quote_and_trade_rejected(kind) -> None:
    with pytest.raises(HistoricalLookaheadError):
        TemporalFirewall(NOW).admit(option(kind, available=NOW + timedelta(microseconds=1)))


def test_future_open_interest_rejected_even_when_row_is_available() -> None:
    row = option("open_interest", identifier="oi1", available=NOW,
                 oi_reference_date=date(2026, 1, 1),
                 oi_available_time=NOW + timedelta(seconds=1),
                 oi_source_semantics="prior official close published later")
    with pytest.raises(HistoricalLookaheadError):
        TemporalFirewall(NOW).admit(row)


def test_open_interest_exact_availability_is_accepted() -> None:
    row = option("open_interest", identifier="oi1", available=NOW,
                 oi_reference_date=date(2026, 1, 1), oi_available_time=NOW,
                 oi_source_semantics="synthetic publication boundary")
    assert TemporalFirewall(NOW).admit(row) is DataQuality.VALID


def test_incomplete_five_minute_bar_rejected_at_0932() -> None:
    start = NOW.replace(hour=9, minute=30)
    row = market(start, available=start + timedelta(minutes=2), kind="bar_5m",
                 bar_start=start, bar_end=start + timedelta(minutes=5),
                 bar_available_time=start + timedelta(minutes=5), is_complete=False)
    with pytest.raises(HistoricalLookaheadError):
        TemporalFirewall(start + timedelta(minutes=2)).admit(row)


def test_complete_five_minute_bar_is_accepted_at_0935() -> None:
    start = NOW.replace(hour=9, minute=30)
    end = start + timedelta(minutes=5)
    row = market(start, available=end, kind="bar_5m", bar_start=start,
                 bar_end=end, bar_available_time=end, is_complete=True)
    assert TemporalFirewall(end).admit(row) is DataQuality.VALID


def test_future_broker_fill_rejected() -> None:
    with pytest.raises(HistoricalLookaheadError):
        TemporalFirewall(NOW).admit(broker(available=NOW + timedelta(seconds=1), kind="fill"))


@pytest.mark.parametrize("transformation", ["calculated_greek", "interpolation", "forward_fill", "rolling_window"])
def test_future_derived_inputs_rejected(transformation) -> None:
    value = HistoricalDerivedValue("derived", 1.0, NOW, NOW, transformation,
                                   ("future-input",), (NOW + timedelta(microseconds=1),))
    with pytest.raises(HistoricalLookaheadError):
        TemporalFirewall(NOW).admit_derived(value)


def test_valid_derived_window_uses_only_past_inputs() -> None:
    value = HistoricalDerivedValue("vwap", 6000.0, NOW, NOW, "rolling_window",
                                   ("m0", "m1"),
                                   (NOW - timedelta(minutes=1), NOW))
    TemporalFirewall(NOW).admit_derived(value)


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        market(datetime(2026, 1, 2, 10, 5))


def test_et_utc_conversion_preserves_instant() -> None:
    assert NOW.astimezone(timezone.utc) == datetime(2026, 1, 2, 15, 5, tzinfo=timezone.utc)


def test_dst_spring_transition_orders_real_instants() -> None:
    before = datetime(2026, 3, 8, 1, 59, 59, tzinfo=ET).astimezone(timezone.utc)
    after = datetime(2026, 3, 8, 3, 0, 0, tzinfo=ET).astimezone(timezone.utc)
    assert after - before == timedelta(seconds=1)


def test_dst_fall_fold_orders_repeated_hour() -> None:
    first = datetime(2026, 11, 1, 1, 30, fold=0, tzinfo=ET).astimezone(timezone.utc)
    second = datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=ET).astimezone(timezone.utc)
    assert second - first == timedelta(hours=1)


def test_out_of_order_rows_rejected() -> None:
    firewall = TemporalFirewall(NOW)
    firewall.admit(market(NOW - timedelta(seconds=1), seq=2))
    with pytest.raises(HistoricalContractError, match="out-of-order"):
        firewall.admit(market(NOW - timedelta(seconds=2), seq=3, identifier="m2"))


def test_duplicate_sequence_rejected() -> None:
    firewall = TemporalFirewall(NOW)
    firewall.admit(market())
    with pytest.raises(HistoricalContractError, match="duplicate"):
        firewall.admit(market(identifier="m2"))


def test_conflicting_duplicate_identifier_rejected() -> None:
    firewall = TemporalFirewall(NOW)
    firewall.admit(market())
    with pytest.raises(HistoricalContractError, match="conflicting duplicate"):
        firewall.admit(market(seq=2, values={"spot": 6001.0}))


def test_test_only_staleness_limit_marks_snapshot_unusable() -> None:
    # 30 seconds is fixture-only and is not an operational runtime threshold.
    old = NOW - timedelta(seconds=31)
    snapshot, audit = HistoricalDatasetAdapter().adapt(
        HistoricalReplayInput(NOW, market=(market(old, available=old),)),
        staleness_limit=timedelta(seconds=30),
    )
    assert snapshot.data_quality.states == (DataQuality.STALE,)
    assert not snapshot.data_quality.usable
    assert audit.stale == audit.unusable_snapshots == 1


def test_missing_required_market_is_explicitly_unusable() -> None:
    snapshot, audit = HistoricalDatasetAdapter().adapt(HistoricalReplayInput(NOW))
    assert snapshot.data_quality.states == (DataQuality.MISSING,)
    assert snapshot.data_quality.usable is False
    assert audit.missing_required == audit.unusable_snapshots == 1


def test_fail_closed_error_carries_deterministic_future_audit() -> None:
    data = HistoricalReplayInput(NOW, market=(market(available=NOW + timedelta(seconds=1)),))
    with pytest.raises(HistoricalLookaheadError) as raised:
        HistoricalDatasetAdapter().adapt(data)
    audit = raised.value.audit_report
    assert audit.rows_seen == audit.rows_rejected == audit.future_rows_rejected == 1
    assert audit.rows_accepted == audit.snapshots_created == 0


def test_fail_closed_error_classifies_incomplete_bar() -> None:
    start = NOW.replace(hour=9, minute=30)
    row = market(start, available=start, kind="bar_5m", bar_start=start,
                 bar_end=start + timedelta(minutes=5),
                 bar_available_time=start + timedelta(minutes=5), is_complete=False)
    with pytest.raises(HistoricalLookaheadError) as raised:
        HistoricalDatasetAdapter().adapt(HistoricalReplayInput(NOW, market=(row,)))
    assert raised.value.audit_report.incomplete_bars == 1
    assert raised.value.audit_report.future_rows_rejected == 0


def test_adapter_audit_and_snapshot_are_deterministic_and_immutable() -> None:
    data = HistoricalReplayInput(NOW, market=(market(),), options=(option(),),
                                 broker=(broker(),), prior_state={"position": "FLAT"})
    first = HistoricalDatasetAdapter().adapt(data)
    second = HistoricalDatasetAdapter().adapt(data)
    assert first == second
    snapshot, audit = first
    assert (audit.rows_seen, audit.rows_accepted, audit.rows_rejected,
            audit.snapshots_created) == (3, 3, 0, 1)
    with pytest.raises(TypeError):
        snapshot.prior_state["position"] = "LONG"
    with pytest.raises(FrozenInstanceError):
        snapshot.replay_time = NOW + timedelta(minutes=1)


def test_synthetic_rows_adapter_to_phase5c3_replay_is_offline_and_safe() -> None:
    snapshot, audit = HistoricalDatasetAdapter().adapt(HistoricalReplayInput(
        NOW, market=(market(values={"spot": 6000.0, "flow_usable": True}),),
        options=(option(),), prior_state={"position": "FLAT"},
    ))
    boundary = snapshot.replay_contract()
    replay = run_replay()
    assert boundary["usable"] and boundary["market"][0]["spot"] == 6000.0
    assert audit.rows_accepted == 2
    assert replay.matrix["unexpected_mismatches"] == 0
    assert replay.matrix["external_activity"] == 0
