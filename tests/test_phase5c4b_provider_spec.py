from dataclasses import replace

import pytest

from bot_spx.historical_provider_spec import (
    Availability, Corrections, DATASET_MANIFEST_FIELDS, FIELD_MAPPINGS,
    MappingStatus, ProviderField, ReplayEligibility,
    historical_replay_eligibility,
)


def row(status=MappingStatus.READY, availability=Availability.DOCUMENTED_PROVIDER_TIME,
        corrections=Corrections.POINT_IN_TIME):
    return ProviderField("synthetic", "synthetic", "value", availability, corrections, status)


@pytest.mark.parametrize(("mapping", "expected"), [
    (row(), ReplayEligibility.ELIGIBLE),
    (row(MappingStatus.READY_WITH_CONSERVATIVE_RULE, Availability.CONSERVATIVE_ASSUMPTION), ReplayEligibility.ELIGIBLE_WITH_CONSERVATIVE_RULE),
    (row(MappingStatus.NEEDS_RECONSTRUCTION), ReplayEligibility.RECONSTRUCT),
    (row(MappingStatus.NEEDS_PROVIDER_CONFIRMATION), ReplayEligibility.BLOCKED_UNRESOLVED),
    (row(MappingStatus.EXCLUDE), ReplayEligibility.EXCLUDED),
])
def test_every_eligibility_class(mapping, expected):
    assert historical_replay_eligibility(mapping) is expected


@pytest.mark.parametrize("mapping", [
    row(availability=Availability.UNRESOLVED),
    row(corrections=Corrections.UNKNOWN),
    row(corrections=Corrections.LATEST_REVISED),
])
def test_unknown_or_revised_semantics_fail_closed(mapping):
    assert historical_replay_eligibility(mapping) is ReplayEligibility.BLOCKED_UNRESOLVED


def test_oi_is_never_intraday_eligible_from_documentation_alone():
    oi = next(item for item in FIELD_MAPPINGS if item.field == "open_interest")
    assert oi.availability is Availability.CONSERVATIVE_ASSUMPTION
    assert historical_replay_eligibility(oi) is ReplayEligibility.BLOCKED_UNRESOLVED


def test_mapping_is_unique_complete_and_declarative():
    names = [item.field for item in FIELD_MAPPINGS]
    assert len(names) == len(set(names))
    assert {"spot", "es_price", "bid", "ask", "bid_size", "ask_size",
            "trade_price", "trade_size", "open_interest", "iv", "gamma",
            "prior_state", "broker_state"} <= set(names)
    assert len(DATASET_MANIFEST_FIELDS) == 13


def test_synthetic_conformance_scenarios():
    explicit = row()
    absent = replace(explicit, availability=Availability.UNRESOLVED)
    delayed_oi = replace(explicit, availability=Availability.CONSERVATIVE_ASSUMPTION,
                         status=MappingStatus.READY_WITH_CONSERVATIVE_RULE)
    revised = replace(explicit, corrections=Corrections.LATEST_REVISED)
    correction_unknown = replace(explicit, corrections=Corrections.UNKNOWN)
    greek = replace(explicit, status=MappingStatus.NEEDS_RECONSTRUCTION)
    sequence_quote_trade = (explicit, replace(explicit, field="trade"))
    assert historical_replay_eligibility(explicit) is ReplayEligibility.ELIGIBLE
    assert historical_replay_eligibility(absent) is ReplayEligibility.BLOCKED_UNRESOLVED
    assert historical_replay_eligibility(delayed_oi) is ReplayEligibility.ELIGIBLE_WITH_CONSERVATIVE_RULE
    assert historical_replay_eligibility(revised) is ReplayEligibility.BLOCKED_UNRESOLVED
    assert historical_replay_eligibility(correction_unknown) is ReplayEligibility.BLOCKED_UNRESOLVED
    assert historical_replay_eligibility(greek) is ReplayEligibility.RECONSTRUCT
    assert len(sequence_quote_trade) == 2
