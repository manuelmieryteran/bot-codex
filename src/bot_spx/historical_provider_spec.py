"""Declarative Phase 5C-4B provider mapping and fail-closed eligibility gate.

There is intentionally no I/O, provider client, credential handling, or runtime
integration in this module.  The evidence behind these declarations is in the
versioned mapping document.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


SPEC_VERSION = "5C-4B.3"
EVIDENCE_LEDGER = "docs/evidence/phase5c4b2_thetadata/evidence_ledger.json"
HUMAN_DECISION_REFERENCE = "FASE 5C-4B.3 — HUMAN MAPPING DECISION CHECKPOINT"


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


class DecisionStatus(str, Enum):
    """Statuses explicitly authorized by the 5C-4B.3 human decision."""

    READY = "READY"
    READY_WITH_CONSERVATIVE_RULE = "READY_WITH_CONSERVATIVE_RULE"
    NEEDS_RECONSTRUCTION = "NEEDS_RECONSTRUCTION"
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    EXCLUDED = "EXCLUDED"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"


@dataclass(frozen=True)
class EvidenceDecision:
    subject: str
    status: DecisionStatus
    confidence: Confidence
    evidence_reference: str
    temporal_semantics: str
    correction_semantics: str
    residual_risk: str
    human_decision_reference: str = HUMAN_DECISION_REFERENCE
    human_decision_status: str = "HUMAN_APPROVED"
    latency_bound: None = None


# This is a decision overlay, not a rewrite or reinterpretation of the immutable
# 5C-4B.2 evidence ledger.  In particular, event time is never treated as proof
# of client available time and no latency bound is manufactured.
HUMAN_MAPPING_DECISIONS = (
    EvidenceDecision(
        "open_interest", DecisionStatus.BLOCKED_UNRESOLVED, Confidence.LOW,
        EVIDENCE_LEDGER,
        "Previous-trading-day OI with OPRA message timestamp; event_time is not proven available_time; no pre-09:30 SLA or guaranteed client availability bound.",
        "Multiple rows may exist and there is no correction flag.",
        "Client availability and authoritative-row selection remain unresolved.",
    ),
    EvidenceDecision(
        "option_trades", DecisionStatus.BLOCKED_UNRESOLVED, Confidence.LOW,
        EVIDENCE_LEDGER,
        "Exchange timestamp only; sequence wraps, is not globally unique, and is not a client receipt time; no maximum latency bound.",
        "Cancels/corrections are tape records with no cancel-to-original link.",
        "Causal receipt ordering and deterministic correction linkage remain unresolved.",
    ),
    EvidenceDecision(
        "option_quotes", DecisionStatus.BLOCKED_UNRESOLVED, Confidence.LOW,
        EVIDENCE_LEDGER,
        "OPRA NBBO with no sequence or receipt time and no maximum latency bound.",
        "Point-in-time correction behavior is not established.",
        "Causal ordering and client availability remain unresolved.",
    ),
    EvidenceDecision(
        "spx_historical_spot", DecisionStatus.BLOCKED_UNRESOLVED, Confidence.LOW,
        EVIDENCE_LEDGER,
        "Cboe Global Indices Feed is separate from OPRA; exchange timestamp only, no shared sequence, and no proven client availability bound.",
        "Point-in-time correction behavior is not established.",
        "Cross-feed causal ordering remains unresolved.",
    ),
    EvidenceDecision(
        "provider_historical_greeks_iv", DecisionStatus.EXCLUDED, Confidence.MEDIUM,
        EVIDENCE_LEDGER,
        "ThetaData historical Greeks/IV are computed at request time, not preserved historical point-in-time outputs.",
        "Request-time recomputation cannot reproduce revisions as-of an historical instant.",
        "Exclusion applies to provider outputs, not to otherwise eligible inputs.",
    ),
    EvidenceDecision(
        "locally_reconstructed_greeks_iv", DecisionStatus.NEEDS_RECONSTRUCTION,
        Confidence.LOW, EVIDENCE_LEDGER,
        "Future reconstruction requires causal option price/quote, underlying and rate; same-date SOFR retrieved retrospectively is not assumed causal before publication; input timestamps are required.",
        "Dividend and expiration conventions, model version, and deterministic implementation must be versioned.",
        "No reconstruction exists and this is not yet replay-eligible.",
    ),
    EvidenceDecision(
        "historical_spxw_0dte_universe",
        DecisionStatus.READY_WITH_CONSERVATIVE_RULE, Confidence.LOW,
        EVIDENCE_LEDGER,
        "For replay date D: root=SPXW, expiration=D, and historical trade/quote activity on D is required.",
        "The activity-derived set is used as observed and historical metadata is not versioned.",
        "May omit listed but inactive contracts, incomplete-metadata contracts, and special holiday/listing circumstances.",
    ),
    EvidenceDecision(
        "provider_capability", DecisionStatus.READY, Confidence.MEDIUM,
        EVIDENCE_LEDGER,
        "Support's tier table is descriptive provider metadata only, not evidence of this account's entitlement.",
        "Capability metadata follows the documented support table.",
        "Provider capability can change and does not grant account access.",
    ),
    EvidenceDecision(
        "our_account_entitlement", DecisionStatus.BLOCKED_UNRESOLVED,
        Confidence.LOW, EVIDENCE_LEDGER,
        "Actual account tier/entitlement is unknown and is not inferred from provider capability.",
        "No independent account-specific entitlement evidence exists.",
        "Access remains blocked until independently verified.",
    ),
)
