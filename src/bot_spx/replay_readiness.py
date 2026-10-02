"""Phase 5C-4B.5A offline causal historical replay readiness contract.

The declarations in this module are an evidence-derived gap inventory, not an
acquisition plan or a replay implementation.  The evaluator is pure and
fail-closed: account acquisition is deliberately not causal eligibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable, Mapping


SPEC_VERSION = "5C-4B.5A"
EVIDENCE_DATE = "2026-01-15"
MAPPING_PROMOTIONS = 0
CUTOVER = "NO"


class ReadinessState(str, Enum):
    RESOLVED = "RESOLVED"
    RESOLVED_WITH_CONSERVATIVE_RULE = "RESOLVED_WITH_CONSERVATIVE_RULE"
    BLOCKED_ACQUISITION = "BLOCKED_ACQUISITION"
    BLOCKED_ENTITLEMENT_AMBIGUITY = "BLOCKED_ENTITLEMENT_AMBIGUITY"
    BLOCKED_AVAILABILITY = "BLOCKED_AVAILABILITY"
    BLOCKED_CORRECTION_POLICY = "BLOCKED_CORRECTION_POLICY"
    BLOCKED_ALIGNMENT = "BLOCKED_ALIGNMENT"
    BLOCKED_STALENESS_POLICY = "BLOCKED_STALENESS_POLICY"
    BLOCKED_METADATA = "BLOCKED_METADATA"
    BLOCKED_HISTORICAL_DEPTH = "BLOCKED_HISTORICAL_DEPTH"
    BLOCKED_RECONSTRUCTION = "BLOCKED_RECONSTRUCTION"
    BLOCKED_VALIDATION = "BLOCKED_VALIDATION"
    BLOCKED_HUMAN_DECISION = "BLOCKED_HUMAN_DECISION"
    EXCLUDED = "EXCLUDED"
    NOT_REQUIRED = "NOT_REQUIRED"
    INVALID = "INVALID"


class Layer(str, Enum):
    PROVIDER_CAPABILITY = "L1_PROVIDER_CAPABILITY"
    ACCOUNT_ACQUISITION = "L2_ACCOUNT_ACQUISITION"
    CAUSAL_INPUT_ELIGIBILITY = "L3_CAUSAL_INPUT_ELIGIBILITY"
    REPLAY_READINESS = "L4_REPLAY_READINESS"


class Priority(str, Enum):
    FOUNDATIONAL_BLOCKER = "FOUNDATIONAL_BLOCKER"
    UPSTREAM_BLOCKER = "UPSTREAM_BLOCKER"
    DOWNSTREAM_BLOCKER = "DOWNSTREAM_BLOCKER"
    OPTIONAL_ENHANCEMENT = "OPTIONAL_ENHANCEMENT"


class SessionStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


class DataRequirement(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    DERIVABLE = "DERIVABLE"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True)
class ComponentAssessment:
    component: str
    state: ReadinessState
    layer: Layer
    evidence: str
    residual_risks: tuple[str, ...]


@dataclass(frozen=True)
class PromotionGate:
    gap_id: str
    current_state: ReadinessState
    required_evidence: tuple[str, ...]
    required_human_decision: tuple[str, ...]
    required_implementation: tuple[str, ...]
    required_tests: tuple[str, ...]
    promotion_target: str
    automatic_promotion_allowed: bool = False


@dataclass(frozen=True)
class Dependency:
    prerequisite: str
    dependent: str


@dataclass(frozen=True)
class SessionReadinessResult:
    status: SessionStatus
    blockers: tuple[str, ...]
    evaluated_requirements: tuple[str, ...]


@dataclass(frozen=True)
class FeatureRequirement:
    feature: str
    raw_inputs: tuple[str, ...]
    derived_inputs: tuple[str, ...]
    trades: DataRequirement
    local_greeks: DataRequirement
    spx: DataRequirement
    oi: DataRequirement
    quotes: DataRequirement
    current_readiness: ReadinessState


@dataclass(frozen=True)
class DepthAssessment:
    component: str
    provider_described_depth: str
    account_verified_depth: str
    required_backtest_depth: str
    state: ReadinessState


@dataclass(frozen=True)
class CorrectionAssessment:
    source: str
    correction_information_available: str
    linked_correction: str
    condition_codes: str
    overwrite_behavior: str
    causal_reconstruction_possible: str
    unresolved_risk: str


ACCOUNT_ACQUISITION_SNAPSHOT = {
    "verified_available": (
        "ACCOUNT_METADATA_ACCESS", "SPX_SPXW_CONTRACT_LIST_ACCESS",
        "OPTION_QUOTE_ACQUISITION", "OPEN_INTEREST_ACQUISITION",
        "PROVIDER_IV_FIRST_ORDER_GREEKS_ACQUISITION", "EOD_GAMMA_ACQUISITION",
        "INTEREST_RATE_HISTORY_ACQUISITION",
    ),
    "option_trades": "AMBIGUOUS/EMPTY_SUCCESS",
    "spx_index_history": "ERROR/TRANSPORT_ERROR/UNRESOLVED",
    "historical_depth": "2026-01-15/SINGLE_DATE_ONLY",
    "account_tier": "NOT_PERSISTED/UNRESOLVED",
    "p2": "ACQUISITION_SCOPE_ANOMALY",
    "p2_row_count": 17_326,
}


COMPONENTS = (
    ComponentAssessment("historical_spxw_0dte_universe", ReadinessState.RESOLVED_WITH_CONSERVATIVE_RULE, Layer.CAUSAL_INPUT_ELIGIBILITY, "root=SPXW, expiration=D and observed trade/quote activity on D; confidence LOW", ("listed but inactive contracts", "incomplete metadata", "unversioned listing/delisting", "holidays and special expirations", "historical calendar/listing changes", "survivorship/inactivity")),
    ComponentAssessment("option_quotes", ReadinessState.BLOCKED_AVAILABILITY, Layer.CAUSAL_INPUT_ELIGIBILITY, "P3 acquisition VERIFIED_AVAILABLE for one contract/date; causal mapping remains BLOCKED_UNRESOLVED", ("exchange event time is not client available time", "no sequence", "corrections unresolved", "zero bid/ask semantics unresolved", "no proven latency bound", "staleness and cross-feed skew unapproved")),
    ComponentAssessment("option_trades", ReadinessState.BLOCKED_ENTITLEMENT_AMBIGUITY, Layer.ACCOUNT_ACQUISITION, "P4 AMBIGUOUS/EMPTY_SUCCESS", ("acquisition cause unresolved", "signed 32-bit sequence wraps and is not globally unique", "late/cancel/correction records are not linked", "historical tape is not received-by-T")),
    ComponentAssessment("open_interest", ReadinessState.BLOCKED_AVAILABILITY, Layer.CAUSAL_INPUT_ELIGIBILITY, "P5 acquisition VERIFIED_AVAILABLE; previous-trading-day OPRA daily OI", ("message time is not client availability", "no pre-open SLA", "multiple messages and no correction flag", "NO_MESSAGE differs from reported ZERO")),
    ComponentAssessment("spx_historical_spot", ReadinessState.BLOCKED_ACQUISITION, Layer.ACCOUNT_ACQUISITION, "P8 ERROR/TRANSPORT_ERROR/UNRESOLVED", ("depth unverified", "available_time unknown", "separate Cboe/OPRA feeds have no shared sequence", "gap and staleness policy absent", "no fallback approved")),
    ComponentAssessment("interest_rate", ReadinessState.BLOCKED_HUMAN_DECISION, Layer.CAUSAL_INPUT_ELIGIBILITY, "P9 acquisition VERIFIED_AVAILABLE; publication_time represented", ("same-date SOFR is published D+1", "no causal rate-selection policy approved")),
    ComponentAssessment("dividend_policy", ReadinessState.BLOCKED_HUMAN_DECISION, Layer.CAUSAL_INPUT_ELIGIBILITY, "local Black-Scholes requires explicit dividend yield", ("ZERO is mathematical/test-only", "historical dividend policy and version are absent")),
    ComponentAssessment("contract_metadata", ReadinessState.BLOCKED_METADATA, Layer.CAUSAL_INPUT_ELIGIBILITY, "P2 supplies expiration/right/strike/symbol only", ("expiration time and settlement style unresolved", "reference/available time and provenance incomplete", "holiday/special listing must fail closed")),
    ComponentAssessment("local_iv_reconstruction", ReadinessState.BLOCKED_RECONSTRUCTION, Layer.REPLAY_READINESS, "LOCAL_SPX_IV_BISECTION_V1 is mathematically tested only", ("causal prerequisites are blocked", "real-input validation absent")),
    ComponentAssessment("local_greeks_reconstruction", ReadinessState.BLOCKED_RECONSTRUCTION, Layer.REPLAY_READINESS, "LOCAL_SPX_BS_V1 is mathematically tested only", ("provider historical Greeks/IV remain EXCLUDED", "causal prerequisites are blocked")),
    ComponentAssessment("cross_feed_temporal_alignment", ReadinessState.BLOCKED_ALIGNMENT, Layer.CAUSAL_INPUT_ELIGIBILITY, "LAST_CAUSALLY_AVAILABLE is represented; EXACT_SYNTHETIC is test-only", ("event/available-time skew limit unapproved", "NEAREST_FUTURE, FUTURE_INTERPOLATION and FUTURE_BACKFILL prohibited")),
    ComponentAssessment("corrections_cancels_policy", ReadinessState.BLOCKED_CORRECTION_POLICY, Layer.CAUSAL_INPUT_ELIGIBILITY, "source-specific correction semantics remain unresolved", ("quotes: no point-in-time behavior", "trades: codes exist but corrections are unlinked", "OI: multiple messages/no flag", "SPX: correction behavior unknown")),
    ComponentAssessment("missingness_policy", ReadinessState.BLOCKED_HUMAN_DECISION, Layer.CAUSAL_INPUT_ELIGIBILITY, "MISSING, ZERO, NO_MESSAGE and UNKNOWN remain distinct", ("silent forward-fill prohibited", "zero imputation requires a future explicit rule")),
    ComponentAssessment("staleness_policy", ReadinessState.BLOCKED_STALENESS_POLICY, Layer.CAUSAL_INPUT_ELIGIBILITY, "no approved max quote age, max SPX age, or cross-feed skew", ("thresholds require empirical coverage/latency evidence and human approval",)),
    ComponentAssessment("session_calendar_expiration", ReadinessState.BLOCKED_METADATA, Layer.CAUSAL_INPUT_ELIGIBILITY, "America/New_York and expiration date=D are necessary but insufficient", ("DST, holidays, early closes, AM/PM settlement and historical listing changes unresolved",)),
    ComponentAssessment("historical_depth", ReadinessState.BLOCKED_HISTORICAL_DEPTH, Layer.ACCOUNT_ACQUISITION, "account evidence covers only 2026-01-15 (SINGLE_DATE_ONLY)", ("provider-described history is not account-verified depth", "required backtest period is HUMAN_DECISION_PENDING")),
    ComponentAssessment("deterministic_provenance", ReadinessState.BLOCKED_VALIDATION, Layer.REPLAY_READINESS, "future records need provider/dataset/identity/times/context and policy/mapping/model/transformation versions", ("bundle schema and validation are not implemented",)),
    ComponentAssessment("replay_bundle_eligibility", ReadinessState.BLOCKED_VALIDATION, Layer.REPLAY_READINESS, "all requested required inputs must independently pass causal gates", ("partial L3 cannot promote L4",)),
    ComponentAssessment("loader_readiness", ReadinessState.NOT_REQUIRED, Layer.REPLAY_READINESS, "loader is outside Phase 5A and was not implemented", ("future work remains blocked by the contract gates",)),
    ComponentAssessment("backtest_readiness", ReadinessState.NOT_REQUIRED, Layer.REPLAY_READINESS, "backtest is outside Phase 5A and was not executed", ("requires a causally eligible loader/session bundle first",)),
)


PROMOTION_GATES = (
    PromotionGate("quotes.available_time", ReadinessState.BLOCKED_AVAILABILITY, ("point-in-time receipt/availability evidence or a defensible bounded availability contract", "quote schema evidence for event ordering, NBBO conditions, and zero values"), ("approve a conservative availability rule without converting event_time directly",), ("versioned point-in-time quote selector preserving MISSING/ZERO/UNKNOWN",), ("future-event rejection", "late-arrival and zero-market fixtures", "no future interpolation/backfill"), "CAUSAL_OPTION_QUOTE"),
    PromotionGate("quotes.corrections", ReadinessState.BLOCKED_CORRECTION_POLICY, ("provider evidence for historical quote revision/correction behavior",), ("approve source-specific as-of policy",), ("deterministic correction-aware selector",), ("late correction known-before/after replay_time",), "POINT_IN_TIME_QUOTES"),
    PromotionGate("trades.acquisition", ReadinessState.BLOCKED_ENTITLEMENT_AMBIGUITY, ("separately authorized non-empty schema observation or explicit denial",), (), ("none in this phase",), ("distinguish empty-valid from denied/error",), "ACCOUNT_ACQUISITION_CLASSIFIED"),
    PromotionGate("trades.tape_semantics", ReadinessState.BLOCKED_CORRECTION_POLICY, ("receipt/availability ordering and deterministic cancel/correction linkage evidence",), ("decide unresolved-record exclusion policy per feature",), ("sequence-wrap-aware point-in-time tape reconstruction",), ("wrap, duplicate, late, cancel, correction and unlinked-record fixtures",), "CAUSAL_TRADE_TAPE"),
    PromotionGate("oi.causal_row", ReadinessState.BLOCKED_AVAILABILITY, ("client available_time evidence and authoritative-row/correction semantics", "coverage evidence distinguishing no message from zero"), ("approve as-of selection, missingness and correction policy",), ("point-in-time OI selector that never assumes 06:30 ET availability",), ("multiple messages", "zero versus no-message", "published after replay_time"), "CAUSAL_OPEN_INTEREST"),
    PromotionGate("spx.acquisition", ReadinessState.BLOCKED_ACQUISITION, ("separately authorized successful account-specific schema observation",), (), ("none in this phase",), ("classify transport error separately from denial and empty success",), "ACCOUNT_ACQUISITION_VERIFIED"),
    PromotionGate("spx.causal_series", ReadinessState.BLOCKED_AVAILABILITY, ("client available_time/depth evidence plus feed gap and correction semantics",), ("approve missingness/staleness policy; no proxy fallback is currently approved",), ("point-in-time selector preserving unchanged-value/no-tick semantics",), ("gaps, stale print, corrections, DST and future print rejection",), "CAUSAL_UNDERLYING"),
    PromotionGate("rate.policy", ReadinessState.BLOCKED_HUMAN_DECISION, ("publication timestamps and value provenance",), ("choose/version last causally published rate, fixed rate, or another explicit policy",), ("as-of publication-time selector",), ("same-date D+1 exclusion", "weekend/holiday and absent publication"), "CAUSAL_RATE"),
    PromotionGate("dividend.policy", ReadinessState.BLOCKED_HUMAN_DECISION, ("historical/versioned dividend-yield evidence if nonzero is proposed",), ("approve/version ZERO or another explicit policy and accept model risk",), ("policy-bound input construction",), ("unapproved ZERO rejection", "version/provenance validation"), "CAUSAL_DIVIDEND"),
    PromotionGate("metadata.contract", ReadinessState.BLOCKED_METADATA, ("historical root, identity, strike/right, expiration time, settlement style, reference/available time and provenance",), ("approve derivation rules for ordinary dates; retain special/holiday fail-closed",), ("versioned metadata/calendar resolver",), ("DST, holiday, early close, AM/PM, SPX/SPXW and special expiration fixtures"), "CAUSAL_CONTRACT_METADATA"),
    PromotionGate("alignment.policy", ReadinessState.BLOCKED_ALIGNMENT, ("both feeds' event and available times plus empirical skew/latency coverage",), ("approve maximum event-time and available-time skew",), ("LAST_CAUSALLY_AVAILABLE selector",), ("reject nearest future/interpolation/backfill", "boundary skew and stale input"), "CAUSAL_ALIGNMENT"),
    PromotionGate("staleness.policy", ReadinessState.BLOCKED_STALENESS_POLICY, ("empirical quote/SPX update cadence, outages, latency and coverage by session regime",), ("approve separate max quote age, max SPX age and cross-feed skew",), ("versioned source-specific age gates",), ("at/beyond boundary", "no threshold means blocked"), "APPROVED_STALENESS"),
    PromotionGate("historical.depth", ReadinessState.BLOCKED_HISTORICAL_DEPTH, ("account-specific earliest/latest accessible dates and representative continuity per required dataset",), ("define required backtest period",), ("offline depth manifest only after authorization",), ("coverage holes and requested period boundaries"), "SUFFICIENT_ACCOUNT_VERIFIED_DEPTH"),
    PromotionGate("local.iv_greeks", ReadinessState.BLOCKED_RECONSTRUCTION, ("causal quote, underlying, rate, dividend, metadata, alignment, staleness and complete provenance",), ("approve all upstream policies and real-replay use",), ("versioned deterministic bridge using LOCAL_SPX_IV_BISECTION_V1, LOCAL_SPX_BS_V1, MID_V1 and ACTUAL_SECONDS_OVER_365_DAYS_V1",), ("repeatability", "real-input contract validation", "failure/no-arbitrage boundaries"), "ELIGIBLE_FOR_REPLAY"),
    PromotionGate("session.bundle", ReadinessState.BLOCKED_VALIDATION, ("eligible inputs and provenance for every requested required feature",), ("approve configuration and mapping versions",), ("pure gate integration before any loader",), ("complete blocker accumulation", "unknown requirement invalid", "one blocked required input blocks session"), "CAUSALLY_REPLAY_ELIGIBLE"),
)


DEPENDENCIES = (
    Dependency("quotes.available_time", "quotes.corrections"),
    Dependency("quotes.corrections", "causal_option_mid"),
    Dependency("spx.acquisition", "spx.causal_series"),
    Dependency("spx.causal_series", "causal_underlying"),
    Dependency("oi.causal_row", "static_oi_gex"),
    Dependency("rate.policy", "causal_rate"),
    Dependency("dividend.policy", "causal_dividend"),
    Dependency("metadata.contract", "causal_contract_metadata"),
    Dependency("alignment.policy", "local.iv_greeks"),
    Dependency("staleness.policy", "local.iv_greeks"),
    Dependency("causal_option_mid", "local.iv_greeks"),
    Dependency("causal_underlying", "local.iv_greeks"),
    Dependency("causal_rate", "local.iv_greeks"),
    Dependency("causal_dividend", "local.iv_greeks"),
    Dependency("causal_contract_metadata", "local.iv_greeks"),
    Dependency("local.iv_greeks", "static_oi_gex"),
    Dependency("trades.acquisition", "trades.tape_semantics"),
    Dependency("trades.tape_semantics", "dealer_flow"),
    Dependency("trades.tape_semantics", "aggressor_classification"),
    Dependency("dealer_flow", "dynamic_gex"),
    Dependency("local.iv_greeks", "dynamic_gex"),
    Dependency("static_oi_gex", "signal_replay"),
    Dependency("dynamic_gex", "signal_replay"),
    Dependency("historical.depth", "session.bundle"),
    Dependency("signal_replay", "session.bundle"),
    Dependency("local.iv_greeks", "session.bundle"),
)


PRIORITIES: Mapping[str, Priority] = {
    "quotes.available_time": Priority.FOUNDATIONAL_BLOCKER,
    "spx.acquisition": Priority.FOUNDATIONAL_BLOCKER,
    "rate.policy": Priority.FOUNDATIONAL_BLOCKER,
    "dividend.policy": Priority.FOUNDATIONAL_BLOCKER,
    "metadata.contract": Priority.FOUNDATIONAL_BLOCKER,
    "oi.causal_row": Priority.FOUNDATIONAL_BLOCKER,
    "trades.acquisition": Priority.OPTIONAL_ENHANCEMENT,
    "quotes.corrections": Priority.UPSTREAM_BLOCKER,
    "spx.causal_series": Priority.UPSTREAM_BLOCKER,
    "alignment.policy": Priority.UPSTREAM_BLOCKER,
    "staleness.policy": Priority.UPSTREAM_BLOCKER,
    "trades.tape_semantics": Priority.OPTIONAL_ENHANCEMENT,
    "local.iv_greeks": Priority.DOWNSTREAM_BLOCKER,
    "historical.depth": Priority.DOWNSTREAM_BLOCKER,
    "session.bundle": Priority.DOWNSTREAM_BLOCKER,
}


FEATURE_REQUIREMENTS = (
    FeatureRequirement("SPX spot", ("spx_index" ,), (), DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, ReadinessState.BLOCKED_ACQUISITION),
    FeatureRequirement("Call Wall", ("option_contracts", "open_interest"), (), DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, DataRequirement.NOT_REQUIRED, ReadinessState.BLOCKED_AVAILABILITY),
    FeatureRequirement("Put Wall", ("option_contracts", "open_interest"), (), DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, DataRequirement.NOT_REQUIRED, ReadinessState.BLOCKED_AVAILABILITY),
    FeatureRequirement("Gamma Flip / Zero Gamma", ("open_interest", "option_quotes", "spx_index", "rate", "dividend", "contract_metadata"), ("local_iv", "local_gamma"), DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Static OI/GEX", ("open_interest", "option_quotes", "spx_index", "rate", "dividend", "contract_metadata"), ("local_gamma",), DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Dynamic GEX", ("option_trades", "option_quotes", "spx_index", "rate", "dividend", "contract_metadata"), ("aggressor_classification", "local_gamma"), DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.OPTIONAL, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Dealer flow", ("option_trades", "option_quotes"), ("aggressor_classification",), DataRequirement.REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_ENTITLEMENT_AMBIGUITY),
    FeatureRequirement("Dealer Dynamic GEX", ("option_trades", "option_quotes", "spx_index", "rate", "dividend", "contract_metadata"), ("dealer_flow", "local_gamma"), DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.NOT_REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Gamma Balance", ("open_interest", "option_quotes", "spx_index", "rate", "dividend", "contract_metadata"), ("static_oi_gex",), DataRequirement.OPTIONAL, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Gamma Regime", ("open_interest", "option_quotes", "spx_index", "rate", "dividend", "contract_metadata"), ("gamma_balance", "gamma_flip"), DataRequirement.OPTIONAL, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Mean Reversion signal", ("spx_index",), ("gamma_regime", "levels"), DataRequirement.OPTIONAL, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Breakout/Breakdown signal", ("spx_index",), ("gamma_regime", "levels"), DataRequirement.OPTIONAL, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_RECONSTRUCTION),
    FeatureRequirement("Risk gate", ("spx_index",), ("signals", "gamma_regime"), DataRequirement.OPTIONAL, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_VALIDATION),
    FeatureRequirement("Entry permission", ("spx_index",), ("risk_gate", "signals"), DataRequirement.OPTIONAL, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, DataRequirement.REQUIRED, ReadinessState.BLOCKED_VALIDATION),
)


TRADE_REQUIREMENTS: Mapping[str, DataRequirement] = {
    "quote_based_iv_reconstruction": DataRequirement.NOT_REQUIRED,
    "dealer_flow_estimation": DataRequirement.REQUIRED,
    "aggressor_classification": DataRequirement.REQUIRED,
    "dynamic_gex": DataRequirement.REQUIRED,
    "signal_reconstruction": DataRequirement.OPTIONAL,
}


DEPTH_MATRIX = tuple(
    DepthAssessment(name, provider_depth, "2026-01-15/SINGLE_DATE_ONLY", "HUMAN_DECISION_PENDING", ReadinessState.BLOCKED_HISTORICAL_DEPTH)
    for name, provider_depth in (
        ("SPXW contracts", "provider-described history; not account proof"),
        ("option quotes", "provider-described history; not account proof"),
        ("option trades", "provider-described history; account entitlement ambiguous"),
        ("open interest", "provider-described daily history; not account proof"),
        ("SPX index", "provider-described index history; acquisition errored"),
        ("interest rates", "provider-described history; not account proof"),
    )
)


CORRECTION_MATRIX = (
    CorrectionAssessment("quotes", "UNRESOLVED", "UNRESOLVED", "bid/ask conditions observed but correction meaning unproven", "UNRESOLVED", "NO", "retrospective record may differ from the quote known at replay_time"),
    CorrectionAssessment("trades", "late/cancel/correction codes documented", "NO", "YES", "UNRESOLVED", "NO", "cancel cannot be deterministically joined to original and sequence wraps"),
    CorrectionAssessment("open_interest", "multiple messages possible; no correction flag", "NO", "NO", "UNRESOLVED", "NO", "latest row may encode a correction unavailable at replay_time"),
    CorrectionAssessment("spx", "UNRESOLVED", "UNRESOLVED", "UNRESOLVED", "UNRESOLVED", "NO", "historical correction and point-in-time revision behavior unknown"),
)


MINIMUM_PROVENANCE_FIELDS = (
    "provider", "dataset", "contract_identity", "event_time", "available_time",
    "source_or_reference_time", "retrieval_context", "policy_version",
    "mapping_version", "model_version", "transformation_version",
)


def validate_dag(dependencies: Iterable[Dependency] = DEPENDENCIES) -> tuple[str, ...]:
    """Return a deterministic topological order or raise for a cyclic graph."""
    edges = tuple(dependencies)
    nodes = {n for edge in edges for n in (edge.prerequisite, edge.dependent)}
    incoming = {node: 0 for node in nodes}
    outgoing = {node: [] for node in nodes}
    for edge in edges:
        outgoing[edge.prerequisite].append(edge.dependent)
        incoming[edge.dependent] += 1
    ready = sorted(node for node, count in incoming.items() if count == 0)
    ordered: list[str] = []
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for target in sorted(outgoing[node]):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
                ready.sort()
    if len(ordered) != len(nodes):
        raise ValueError("readiness dependency graph contains a cycle")
    return tuple(ordered)


def evaluate_session_replay_readiness(
    required_inputs: Iterable[str], eligibility: Mapping[str, ReadinessState]
) -> SessionReadinessResult:
    """Evaluate declarations only; never loads data or infers eligibility.

    Unknown requirements are INVALID.  Every non-RESOLVED required input is
    returned, rather than stopping at the first blocker.  A conservative-rule
    input is accepted only because the caller explicitly supplied that closed
    state; no automatic layer promotion occurs here.
    """
    required = tuple(dict.fromkeys(required_inputs))
    if not required:
        return SessionReadinessResult(SessionStatus.INVALID, ("required_inputs:EMPTY",), required)
    unknown = tuple(f"{item}:UNKNOWN" for item in required if item not in eligibility)
    if unknown:
        return SessionReadinessResult(SessionStatus.INVALID, unknown, required)
    accepted = {ReadinessState.RESOLVED, ReadinessState.RESOLVED_WITH_CONSERVATIVE_RULE}
    blockers = tuple(f"{item}:{eligibility[item].value}" for item in required if eligibility[item] not in accepted)
    return SessionReadinessResult(SessionStatus.BLOCKED if blockers else SessionStatus.READY, blockers, required)


def contract_dict() -> dict[str, object]:
    """Return the complete contract as JSON-compatible primitives."""
    def encode(value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, tuple):
            return [encode(item) for item in value]
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        if hasattr(value, "__dataclass_fields__"):
            return encode(asdict(value))
        return value

    return {
        "schema_version": "1.0",
        "phase": SPEC_VERSION,
        "evidence_date": EVIDENCE_DATE,
        "mapping_promotions": MAPPING_PROMOTIONS,
        "cutover": CUTOVER,
        "account_acquisition_snapshot": encode(ACCOUNT_ACQUISITION_SNAPSHOT),
        "components": encode(COMPONENTS),
        "promotion_gates": encode(PROMOTION_GATES),
        "dependencies": encode(DEPENDENCIES),
        "topological_order": list(validate_dag()),
        "priorities": encode(dict(PRIORITIES)),
        "feature_requirements": encode(FEATURE_REQUIREMENTS),
        "trade_requirements": encode(dict(TRADE_REQUIREMENTS)),
        "depth_matrix": encode(DEPTH_MATRIX),
        "correction_matrix": encode(CORRECTION_MATRIX),
        "minimum_provenance_fields": list(MINIMUM_PROVENANCE_FIELDS),
        "next_minimum_phase": "offline human policy/evidence specification for causal timestamps, source-specific corrections, missingness, staleness, alignment, calendar/metadata and required depth; no acquisition or loader",
    }
