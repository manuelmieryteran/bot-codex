"""Declarative Phase 5C-4B provider mapping and fail-closed eligibility gate.

There is intentionally no I/O, provider client, credential handling, or runtime
integration in this module.  The evidence behind these declarations is in the
versioned mapping document.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


SPEC_VERSION = "5C-4B.1"


class Availability(str, Enum):
    DOCUMENTED_PROVIDER_TIME = "DOCUMENTED_PROVIDER_TIME"
    DOCUMENTED_EXCHANGE_TIME = "DOCUMENTED_EXCHANGE_TIME"
    CONSERVATIVE_ASSUMPTION = "CONSERVATIVE_ASSUMPTION"
    UNRESOLVED = "UNRESOLVED"


class Corrections(str, Enum):
    POINT_IN_TIME = "POINT_IN_TIME"
    LATEST_REVISED = "LATEST_REVISED"
    UNKNOWN = "UNKNOWN"


class MappingStatus(str, Enum):
    READY = "READY"
    READY_WITH_CONSERVATIVE_RULE = "READY_WITH_CONSERVATIVE_RULE"
    NEEDS_RECONSTRUCTION = "NEEDS_RECONSTRUCTION"
    NEEDS_PROVIDER_CONFIRMATION = "NEEDS_PROVIDER_CONFIRMATION"
    UNAVAILABLE = "UNAVAILABLE"
    EXCLUDE = "EXCLUDE"


class ReplayEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_CONSERVATIVE_RULE = "ELIGIBLE_WITH_CONSERVATIVE_RULE"
    RECONSTRUCT = "RECONSTRUCT"
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    EXCLUDED = "EXCLUDED"


@dataclass(frozen=True)
class ProviderField:
    field: str
    provider: str
    provider_field: str | None
    availability: Availability
    corrections: Corrections
    status: MappingStatus
    required_for_replay: bool = True


def historical_replay_eligibility(mapping: ProviderField) -> ReplayEligibility:
    """Classify one declaration; uncertainty always fails closed."""
    if mapping.status in (MappingStatus.EXCLUDE, MappingStatus.UNAVAILABLE):
        return ReplayEligibility.EXCLUDED
    if mapping.status is MappingStatus.NEEDS_RECONSTRUCTION:
        return ReplayEligibility.RECONSTRUCT
    if (
        mapping.status is MappingStatus.NEEDS_PROVIDER_CONFIRMATION
        or mapping.availability is Availability.UNRESOLVED
        or mapping.corrections is not Corrections.POINT_IN_TIME
    ):
        return ReplayEligibility.BLOCKED_UNRESOLVED
    if (
        mapping.status is MappingStatus.READY_WITH_CONSERVATIVE_RULE
        or mapping.availability is Availability.CONSERVATIVE_ASSUMPTION
    ):
        return ReplayEligibility.ELIGIBLE_WITH_CONSERVATIVE_RULE
    return ReplayEligibility.ELIGIBLE


# Fields are the 5C-4A raw/derived inventory. Critical ThetaData records remain
# blocked until receipt/availability and revision semantics are confirmed.
FIELD_MAPPINGS = (
    ProviderField("spot", "ThetaData", "index price ms_of_day/date", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("es_price", "QuantConnect/TradeStation", "future trade/bar", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("bid", "ThetaData", "bid", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("ask", "ThetaData", "ask", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("bid_size", "ThetaData", "bid_size", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("ask_size", "ThetaData", "ask_size", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("trade_price", "ThetaData", "price", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("trade_size", "ThetaData", "size", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("open_interest", "ThetaData", "open_interest", Availability.CONSERVATIVE_ASSUMPTION, Corrections.UNKNOWN, MappingStatus.NEEDS_PROVIDER_CONFIRMATION),
    ProviderField("iv", "ThetaData/local", "implied_vol", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_RECONSTRUCTION),
    ProviderField("delta", "ThetaData/local", "delta", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_RECONSTRUCTION),
    ProviderField("gamma", "ThetaData/local", "gamma", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_RECONSTRUCTION),
    ProviderField("other_greeks", "ThetaData/local", "theta/vega/rho/...", Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.NEEDS_RECONSTRUCTION),
    ProviderField("bar_metadata", "local", "bar_start/bar_end/available/complete", Availability.CONSERVATIVE_ASSUMPTION, Corrections.POINT_IN_TIME, MappingStatus.READY_WITH_CONSERVATIVE_RULE, False),
    ProviderField("derived_strategy_fields", "local", None, Availability.DOCUMENTED_PROVIDER_TIME, Corrections.POINT_IN_TIME, MappingStatus.NEEDS_RECONSTRUCTION),
    ProviderField("prior_state", "local replay", None, Availability.DOCUMENTED_PROVIDER_TIME, Corrections.POINT_IN_TIME, MappingStatus.READY),
    ProviderField("broker_state", "TradeStation", None, Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.EXCLUDE, False),
    ProviderField("credentials_pnl_cloud", "none", None, Availability.UNRESOLVED, Corrections.UNKNOWN, MappingStatus.EXCLUDE, False),
)


DATASET_MANIFEST_FIELDS = (
    "provider", "dataset_type", "symbol", "date_range", "downloaded_at",
    "provider_version", "schema_version", "query_parameters", "raw_file_hash",
    "adapter_version", "mapping_spec_version", "timezone", "notes",
)
