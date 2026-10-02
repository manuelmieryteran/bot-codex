"""Synthetic validation of the Phase 5C-4B.4B causal contract."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bot_spx.causal_greeks_inputs import *
from bot_spx.historical_provider_spec import HUMAN_MAPPING_DECISIONS, DecisionStatus
from bot_spx.local_greeks import ContractStatus, RatePolicy


T = datetime(2025, 1, 15, 15, 0, tzinfo=timezone.utc)
PROVENANCE = CausalInputProvenance("SYNTHETIC", "id", "point-in-time", True, True)


def observation(kind, value, *, event=T - timedelta(seconds=2), available=T - timedelta(seconds=1),
                mapping=MappingStatus.SYNTHETIC_TEST_ONLY,
                stale=StalenessPolicy.EXPLICIT_TEST_THRESHOLD,
                correction=CorrectionStatus.POINT_IN_TIME,
                missing=Missingness.PRESENT):
    return CausalInputObservation(kind, value, "index_points", event, event, available, T,
        "SYNTHETIC", kind.value, None, correction, QualityStatus.VALID, stale,
        PROVENANCE, mapping, missing, timedelta(minutes=5))


def components():
    identity = "SPXW-20250115-C-6000"
    option = observation(InputKind.OPTION_QUOTE, OptionQuoteValue(19.0, 21.0, identity))
    underlying = observation(InputKind.UNDERLYING_SPX, 6000.0)
    rate_value = RateValue(.04, T - timedelta(days=1), T - timedelta(hours=1),
                           RatePolicy.EXPLICIT_CAUSAL_RATE, "SYNTHETIC_V1")
    rate = observation(InputKind.RATE, rate_value)
    dividend = DividendInput(0.0, DividendEvidencePolicy.ZERO, "TEST_ZERO_V1")
    metadata = ContractMetadata("SPXW", T.date(), T + timedelta(hours=6), 6000.0,
        OptionRight.CALL, "PM_CASH", identity, "SYNTHETIC", T - timedelta(days=1),
        T - timedelta(hours=2), "synthetic fixture", MetadataStatus.SYNTHETIC_COMPLETE)
    return option, underlying, rate, dividend, metadata


def build(**overrides):
    option, underlying, rate, dividend, metadata = components()
    values = dict(replay_time=T, option=option, underlying=underlying, rate=rate,
                  dividend=dividend, metadata=metadata,
                  alignment_method=AlignmentMethod.LAST_CAUSALLY_AVAILABLE,
                  test_only=True)
    values.update(overrides)
    return build_causal_greeks_input_bundle(**values)


def test_complete_synthetic_bundle_is_test_only_and_deterministic():
    first = build()
    second = build()
    assert first == second
    assert first.eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
    assert first.bundle is not None


@pytest.mark.parametrize(("field", "status"), [
    ("option", EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY),
    ("underlying", EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY),
    ("rate", EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY),
])
def test_available_after_replay_is_blocked(field, status):
    items = dict(zip(("option", "underlying", "rate", "dividend", "metadata"), components()))
    items[field] = replace(items[field], available_time=T + timedelta(microseconds=1))
    assert build(**{field: items[field]}).eligibility.status is status


@pytest.mark.parametrize("field", ["option", "underlying", "rate"])
def test_all_components_are_required(field):
    assert build(**{field: None}).eligibility.status is EligibilityStatus.BLOCKED_MISSING


def test_equal_event_time_does_not_override_future_availability():
    option, underlying, *_ = components()
    option = replace(option, event_time=underlying.event_time, available_time=T + timedelta(seconds=1))
    assert build(option=option).eligibility.status is EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY


@pytest.mark.parametrize("option_delta,underlying_delta", [(5, 2), (2, 5), (2, 2)])
def test_cross_feed_skew_is_explicit_and_not_assumed_simultaneous(option_delta, underlying_delta):
    option, underlying, *_ = components()
    result = build(option=replace(option, event_time=T - timedelta(seconds=option_delta)),
                   underlying=replace(underlying, event_time=T - timedelta(seconds=underlying_delta)))
    assert result.bundle.alignment.event_time_skew == timedelta(seconds=underlying_delta-option_delta)
    assert result.bundle.alignment.available_time_skew == timedelta(0)


def test_future_event_and_naive_timestamp_fail_closed():
    option, *_ = components()
    assert build(option=replace(option, event_time=T + timedelta(seconds=1))).eligibility.status is EligibilityStatus.BLOCKED_FUTURE_EVENT
    assert build(option=replace(option, event_time=T.replace(tzinfo=None))).eligibility.status is EligibilityStatus.INVALID_INPUT


def test_missing_availability_cannot_be_synthesized_from_average_latency():
    option, *_ = components()
    result = build(option=replace(option, available_time=None))
    assert result.eligibility.status is EligibilityStatus.BLOCKED_UNRESOLVED_AVAILABILITY
    assert result.bundle is None


def test_real_option_and_spx_mappings_never_eligible():
    option, underlying, *_ = components()
    assert build(option=replace(option, mapping_status=MappingStatus.BLOCKED_UNRESOLVED)).eligibility.status is EligibilityStatus.BLOCKED_MAPPING
    assert build(underlying=replace(underlying, mapping_status=MappingStatus.BLOCKED_UNRESOLVED)).eligibility.status is EligibilityStatus.BLOCKED_MAPPING
    assert real_historical_spx_local_greeks_eligibility().status is not EligibilityStatus.ELIGIBLE


def test_unresolved_and_explicit_test_staleness():
    option, *_ = components()
    assert build(option=replace(option, staleness_policy=StalenessPolicy.NO_THRESHOLD_APPROVED)).eligibility.status is EligibilityStatus.BLOCKED_STALENESS_POLICY
    assert build().eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
    assert build(test_only=False).eligibility.status is EligibilityStatus.BLOCKED_STALENESS_POLICY


@pytest.mark.parametrize("method", [AlignmentMethod.NEAREST_FUTURE,
                                    AlignmentMethod.FUTURE_INTERPOLATION,
                                    AlignmentMethod.FUTURE_BACKFILL])
def test_future_selection_methods_are_prohibited(method):
    assert build(alignment_method=method).eligibility.status is EligibilityStatus.BLOCKED_ALIGNMENT


def test_same_day_retrospective_sofr_and_future_publication_are_blocked():
    *_, rate, dividend, metadata = components()
    retrospective = replace(rate, value=replace(rate.value, reference_time=T,
                            publication_time=T + timedelta(days=1)))
    assert build(rate=retrospective).eligibility.status is EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY
    assert build(rate=replace(rate, value=replace(rate.value, publication_time=T + timedelta(seconds=1)))).eligibility.status is EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY


def test_prior_published_rate_is_usable_but_missing_publication_is_not():
    rate = components()[2]
    assert build().eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
    assert build(rate=replace(rate, value=replace(rate.value, publication_time=None))).eligibility.status is EligibilityStatus.BLOCKED_UNRESOLVED_AVAILABILITY


def test_unapproved_rate_fallback_is_blocked():
    rate = components()[2]
    fallback = replace(rate, value=replace(rate.value, policy=RatePolicy.VERSIONED_APPROVED_FALLBACK))
    assert build(rate=fallback).eligibility.status is EligibilityStatus.BLOCKED_UNRESOLVED_POLICY


def test_dividend_policy_missing_and_zero_is_mathematical_only():
    assert build(dividend=None).eligibility.status is EligibilityStatus.BLOCKED_MISSING
    assert build().eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
    assert build(test_only=False).eligibility.status is EligibilityStatus.BLOCKED_STALENESS_POLICY


def test_metadata_complete_conservative_and_unresolved_cases():
    metadata = components()[4]
    assert build(metadata=replace(metadata, contract_identity="")).eligibility.status is EligibilityStatus.INVALID_INPUT
    conservative = replace(metadata, status=MetadataStatus.CONSERVATIVE_SPXW)
    assert build(metadata=conservative).eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
    special = replace(metadata, status=MetadataStatus.SPECIAL_CASE_UNRESOLVED)
    assert build(metadata=special).eligibility.status is EligibilityStatus.BLOCKED_UNRESOLVED_POLICY


def test_correction_policy_is_explicit_and_unresolved_is_blocked():
    option = components()[0]
    assert build(option=replace(option, correction_status=CorrectionStatus.UNRESOLVED)).eligibility.status is EligibilityStatus.BLOCKED_CORRECTION_POLICY


def test_no_message_is_not_zero_and_no_forward_fill_occurs():
    option = components()[0]
    no_message = replace(option, missingness=Missingness.NO_MESSAGE)
    zero = replace(option, missingness=Missingness.ZERO,
                   value=OptionQuoteValue(0.0, 0.0, option.value.contract_identity))
    assert build(option=no_message).eligibility.status is EligibilityStatus.BLOCKED_MISSING
    assert build(option=zero).eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY


def test_blocked_bundle_cannot_call_engine_and_test_bundle_can():
    complete = build().bundle
    assert complete is not None
    assert execute_local_greeks(complete).status is ContractStatus.SOLVED
    blocked = replace(complete, eligibility=CausalEligibilityResult(EligibilityStatus.BLOCKED_MAPPING))
    with pytest.raises(ValueError, match="blocked causal bundle"):
        execute_local_greeks(blocked)


def test_out_of_order_arrival_is_compatible_with_availability_firewall():
    option, underlying, *_ = components()
    option = replace(option, sequence=9, event_time=T - timedelta(seconds=10), available_time=T - timedelta(seconds=1))
    underlying = replace(underlying, sequence=2, event_time=T - timedelta(seconds=3), available_time=T - timedelta(seconds=2))
    assert build(option=option, underlying=underlying).eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY


def test_mapping_runtime_evidence_and_network_integrity():
    decisions = {row.subject: row.status for row in HUMAN_MAPPING_DECISIONS}
    assert len(decisions) == 9
    assert decisions["provider_historical_greeks_iv"] is DecisionStatus.EXCLUDED
    assert decisions["locally_reconstructed_greeks_iv"] is DecisionStatus.NEEDS_RECONSTRUCTION
    for name in ("spx_historical_spot", "open_interest", "option_trades", "option_quotes"):
        assert decisions[name] is DecisionStatus.BLOCKED_UNRESOLVED
    assert decisions["historical_spxw_0dte_universe"] is DecisionStatus.READY_WITH_CONSERVATIVE_RULE
    module = Path("src/bot_spx/causal_greeks_inputs.py").read_text()
    forbidden = ("requests", "urllib", "socket", "dotenv", "subprocess", "TradeStation", "DigitalOcean")
    assert not any(f"import {name}" in module or f"from {name}" in module for name in forbidden)
    for runtime in ("spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py", "spx_data_FASE5.py"):
        text = Path(runtime).read_text()
        assert "causal_greeks_inputs" not in text and "local_greeks" not in text
    assert "cutover=NO" in Path("docs/evidence/phase5c4b3_human_mapping_decision.md").read_text()
