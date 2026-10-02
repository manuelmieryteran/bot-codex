"""Phase 5C-4B.5B causal policy and evidence resolution contract.

This module is deliberately declarative.  It does not acquire evidence, select
a policy, promote a mapping, or integrate with a runtime.  Immutable records
describe the exact gates that a later, separately authorised phase must clear.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable


SPEC_VERSION = "5C-4B.5B"
SOURCE_PHASE = "5C-4B.5A"
MAPPING_PROMOTIONS = 0
CUTOVER = "NO"
CURRENT_SESSION_STATUS = "BLOCKED"
CURRENT_BLOCKER_COUNT = 19


class DocketStatus(str, Enum):
    EVIDENCE_SUFFICIENT_DECISION_PENDING = "EVIDENCE_SUFFICIENT_DECISION_PENDING"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    ACCOUNT_VERIFICATION_REQUIRED = "ACCOUNT_VERIFICATION_REQUIRED"
    POLICY_DEFINITION_REQUIRED = "POLICY_DEFINITION_REQUIRED"
    IMPLEMENTATION_REQUIRED = "IMPLEMENTATION_REQUIRED"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    BLOCKED_UPSTREAM = "BLOCKED_UPSTREAM"
    EXCLUDED = "EXCLUDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DecisionRequirement(str, Enum):
    NONE = "NONE"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    EVIDENCE_FIRST = "EVIDENCE_FIRST"
    IMPLEMENTATION_FIRST = "IMPLEMENTATION_FIRST"
    UPSTREAM_FIRST = "UPSTREAM_FIRST"


class EvidenceStatus(str, Enum):
    PERSISTED_SUFFICIENT = "PERSISTED_SUFFICIENT"
    PERSISTED_PARTIAL = "PERSISTED_PARTIAL"
    PERSISTED_INSUFFICIENT = "PERSISTED_INSUFFICIENT"
    NOT_OBSERVED = "NOT_OBSERVED"
    CONTRADICTORY = "CONTRADICTORY"


class DecisionPacketStatus(str, Enum):
    PENDING = "PENDING"


class ActionClass(str, Enum):
    HUMAN_DECISION = "HUMAN_DECISION"
    OFFLINE_IMPLEMENTATION = "OFFLINE_IMPLEMENTATION"
    CONTROLLED_EVIDENCE_ACQUISITION = "CONTROLLED_EVIDENCE_ACQUISITION"
    VALIDATION = "VALIDATION"
    BLOCKED_UPSTREAM = "BLOCKED_UPSTREAM"


@dataclass(frozen=True)
class BlockerDocket:
    blocker_id: str
    name: str
    component: str
    current_readiness_state: str
    technical_priority: str
    upstream_dependencies: tuple[str, ...]
    downstream_dependents: tuple[str, ...]
    does_not_unlock: tuple[str, ...]
    persisted_evidence_refs: tuple[str, ...]
    persisted_evidence_summary: tuple[str, ...]
    evidence_status: EvidenceStatus
    missing_evidence: tuple[str, ...]
    human_decision_required: DecisionRequirement
    decision_question: str
    admissible_decision_classes: tuple[str, ...]
    prohibited_decision_classes: tuple[str, ...]
    lookahead_risk: str
    residual_risks: tuple[str, ...]
    required_future_implementation: tuple[str, ...]
    required_future_tests: tuple[str, ...]
    promotion_target: str
    promotion_preconditions: tuple[str, ...]
    automatic_promotion_allowed: bool
    reprobe_required: bool
    external_data_required: bool
    runtime_change_required: bool
    notes: tuple[str, ...]
    status: DocketStatus


@dataclass(frozen=True)
class HumanDecisionPacket:
    decision_id: str
    related_blockers: tuple[str, ...]
    question: str
    why_needed: str
    evidence_available: tuple[str, ...]
    evidence_missing: tuple[str, ...]
    admissible_options: tuple[str, ...]
    prohibited_options: tuple[str, ...]
    downstream_effect: tuple[str, ...]
    residual_risk: tuple[str, ...]
    reversible: bool
    requires_new_external_evidence: bool
    requires_future_authorization: bool
    status: DecisionPacketStatus = DecisionPacketStatus.PENDING


@dataclass(frozen=True)
class EvidenceRequest:
    evidence_id: str
    related_blockers: tuple[str, ...]
    question_answered: str
    minimum_scope: tuple[str, ...]
    source_class: str
    external_call_required: bool
    credential_required: bool
    human_authorization_required: bool
    raw_payload_retention: str
    expected_outcomes: tuple[str, ...]
    stop_conditions: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionEdge:
    prerequisite: str
    dependent: str


@dataclass(frozen=True)
class NextAction:
    action_id: str
    action_class: ActionClass
    related_blockers: tuple[str, ...]
    prerequisite_actions: tuple[str, ...]
    description: str
    execute_in_this_phase: bool = False


REF_PROVIDER = "src/bot_spx/historical_provider_spec.py"
REF_CAUSAL = "src/bot_spx/causal_greeks_inputs.py"
REF_5A = "docs/evidence/phase5c4b5a_replay_readiness.json"
REF_LEDGER = "docs/evidence/phase5c4b2_thetadata/evidence_ledger.json"
REF_ACCOUNT = "docs/evidence/phase5c4b4c2_thetadata_account/evidence_summary.json"


def _d(
    blocker_id: str, name: str, component: str, state: str, priority: str,
    upstream: tuple[str, ...], downstream: tuple[str, ...], refs: tuple[str, ...],
    evidence: tuple[str, ...], evidence_status: EvidenceStatus,
    missing: tuple[str, ...], requirement: DecisionRequirement, question: str,
    admissible: tuple[str, ...], prohibited: tuple[str, ...], lookahead: str,
    risks: tuple[str, ...], implementation: tuple[str, ...], tests: tuple[str, ...],
    target: str, preconditions: tuple[str, ...], *, reprobe: bool = False,
    external: bool = False, runtime: bool = True,
    status: DocketStatus = DocketStatus.POLICY_DEFINITION_REQUIRED,
    notes: tuple[str, ...] = (),
) -> BlockerDocket:
    return BlockerDocket(
        blocker_id, name, component, state, priority, upstream, downstream,
        ("NO_COMPONENT_BY_ITSELF", "UNRELATED_BRANCHES", "LOADER_BACKTEST_MAPPING_AND_CUTOVER"), refs,
        evidence, evidence_status, missing, requirement, question, admissible,
        prohibited, lookahead, risks, implementation, tests, target,
        preconditions, False, reprobe, external, runtime, notes, status,
    )


DOCKETS = (
    _d("B01", "QUOTE_AVAILABLE_TIME", "option_quotes", "BLOCKED_UNRESOLVED", "FOUNDATIONAL_BLOCKER", (), ("B02", "B03", "B11"), (REF_PROVIDER, REF_ACCOUNT, REF_5A),
       ("OPRA NBBO and option event timestamp are persisted", "account quote acquisition is VERIFIED_AVAILABLE", "sequence and receipt time are absent", "historical download does not prove client availability"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("provider receipt/availability timestamp, or documented deterministic maximum latency bound", "coverage proving the bound for the intended historical product/account"), DecisionRequirement.EVIDENCE_FIRST,
       "Which evidence-backed transform establishes when each quote was knowable to the client?",
       ("PROVIDER_SUPPLIED_AVAILABILITY_TIME", "DETERMINISTIC_LATENCY_UPPER_BOUND", "CONSERVATIVE_HUMAN_APPROVED_TRANSFORM", "FAIL_CLOSED_EXCLUSION"),
       ("EVENT_TIME_EQUALS_AVAILABLE_TIME_WITHOUT_EVIDENCE", "AVERAGE_LATENCY", "FUTURE_TICK", "RETROSPECTIVE_DOWNLOAD_TIME"),
       "Treating exchange event time or a retrospective artifact as availability admits quotes not known by replay time.",
       ("clock-domain uncertainty", "tail latency beyond a documented bound", "excluded observations reduce coverage"),
       ("versioned as-of quote selector", "preserve event_time, available_time and provenance"),
       ("reject available_time after replay_time", "bound boundary and late-arrival fixtures", "reject missing availability"),
       "CAUSAL_OPTION_QUOTE_TIME", ("external evidence retained", "human policy approval", "implementation and validation complete"), external=True),
    _d("B02", "QUOTE_CORRECTION_POLICY", "option_quotes", "BLOCKED_UNRESOLVED", "UPSTREAM_BLOCKER", ("B01",), ("B11",), (REF_PROVIDER, REF_LEDGER, REF_5A),
       ("bid/ask condition fields were observed", "no sequence, correction flag, replacement semantics or linked correction was demonstrated"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("provider semantics for corrections and condition codes", "point-in-time replacement/linkage behavior"), DecisionRequirement.EVIDENCE_FIRST,
       "After provider semantics are known, how must corrected, invalid, crossed, locked, zero-bid and zero-ask quotes be classified as of T?",
       ("CONDITION_AWARE_AS_OF_SELECTION", "EXCLUDE_UNRESOLVED_CONDITIONS", "FAIL_CLOSED_SOURCE_EXCLUSION"),
       ("LATEST_ROW_WINS", "RETROSPECTIVE_OVERWRITE", "ZERO_AS_MISSING_WITHOUT_POLICY", "INVENTED_CORRECTION_LINKAGE"),
       "A correction observed after T can overwrite the quote actually known at T.",
       ("unknown codes remain excluded", "crossed/locked markets may be valid or erroneous by venue semantics", "coverage loss"),
       ("versioned condition/correction classifier", "separate provider facts from approved policy outcomes"),
       ("corrected-before/after-T", "invalid/crossed/locked", "zero bid and zero ask", "unknown code fails closed"),
       "POINT_IN_TIME_QUOTES", ("B01 promoted", "provider semantics persisted", "human policy approval", "tests pass"), external=True),
    _d("B03", "QUOTE_STALENESS_POLICY", "option_quotes", "NO_THRESHOLD_APPROVED", "UPSTREAM_BLOCKER", ("B01",), ("B11",), (REF_5A,),
       ("no maximum quote age is approved",), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("empirical quote update cadence, outages, latency and session-regime coverage",), DecisionRequirement.EVIDENCE_FIRST,
       "What versioned maximum quote age, if any, is acceptable per session regime?",
       ("EMPIRICAL_HUMAN_APPROVED_THRESHOLD", "FAIL_CLOSED_NO_REUSE", "SOURCE_OR_REGIME_SPECIFIC_THRESHOLDS"),
       ("INVENTED_SECONDS_OR_MILLISECONDS", "SPX_AGE_AS_QUOTE_AGE", "CROSS_FEED_SKEW_AS_QUOTE_AGE", "SILENT_UNBOUNDED_REUSE"),
       "An old quote can be paired with later inputs and appear contemporaneous.", ("threshold model error", "coverage loss near outages"),
       ("versioned independent quote-age gate",), ("no threshold remains blocked", "at/beyond-boundary", "outage and missing timestamp fail closed"),
       "APPROVED_QUOTE_STALENESS", ("B01 promoted", "empirical evidence", "human approval", "tests pass"), external=True),
    _d("B04", "OI_AVAILABLE_TIME", "open_interest", "BLOCKED_UNRESOLVED", "FOUNDATIONAL_BLOCKER", (), ("B05", "B06"), (REF_PROVIDER, REF_ACCOUNT, REF_5A),
       ("OI denotes previous-trading-day OI", "OPRA daily-message timestamp exists", "multiple messages are possible", "there is no demonstrated pre-09:30 SLA", "message event time is not client availability"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("client receipt/availability evidence or deterministic bound", "coverage across relevant publication regimes"), DecisionRequirement.EVIDENCE_FIRST,
       "When was each OI message causally available to the client?",
       ("PROVIDER_SUPPLIED_AVAILABILITY_TIME", "DETERMINISTIC_LATENCY_UPPER_BOUND", "CONSERVATIVE_APPROVED_TRANSFORM", "EXCLUSION"),
       ("MESSAGE_TIME_AUTOMATICALLY_EQUALS_AVAILABLE_TIME", "ASSUMED_PREOPEN_SLA", "RETROSPECTIVE_DOWNLOAD_TIME"),
       "A daily message can be selected before it reached the client.", ("publication and transport variability", "coverage loss"),
       ("point-in-time OI message selector",), ("published/received after T rejected", "multiple-message ordering", "missing availability rejected"),
       "CAUSAL_OI_TIME", ("availability evidence", "human approval", "implementation and validation"), external=True),
    _d("B05", "OI_CORRECTION_POLICY", "open_interest", "BLOCKED_UNRESOLVED", "UPSTREAM_BLOCKER", ("B04",), ("B06",), (REF_PROVIDER, REF_5A),
       ("multiple OI rows/messages may occur", "no correction flag or linked replacement is demonstrated"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("message replacement/conflict semantics", "evidence permitting correction detection and provenance"), DecisionRequirement.EVIDENCE_FIRST,
       "How are multiple causally available OI messages, conflicts and possible replacements resolved?",
       ("PROVEN_REPLACEMENT_SEMANTICS", "LATEST_KNOWN_MESSAGE_AFTER_AVAILABILITY_PROOF", "EXCLUDE_CONFLICTS"),
       ("LATEST_ROW_WINS_AUTOMATICALLY", "RETROSPECTIVE_OVERWRITE", "INVENTED_CORRECTION_FLAG"),
       "A later correction can leak into an earlier replay state.", ("unflagged correction ambiguity", "excluded conflicts"),
       ("provenance-preserving as-of conflict resolver",), ("conflict fixtures", "later-known replacement excluded at earlier T", "deterministic provenance"),
       "POINT_IN_TIME_OI_MESSAGES", ("B04 promoted", "replacement semantics", "human approval", "tests pass"), external=True),
    _d("B06", "OI_MISSINGNESS_POLICY", "open_interest", "BLOCKED_UNRESOLVED", "UPSTREAM_BLOCKER", ("B04", "B05"), (), (REF_PROVIDER, REF_5A),
       ("absence of a message can mean no reportable OI exists", "MISSING, ZERO, NO_MESSAGE and UNKNOWN are distinct"), EvidenceStatus.PERSISTED_PARTIAL,
       ("coverage evidence distinguishing no message from acquisition/coverage failure",), DecisionRequirement.EVIDENCE_FIRST,
       "For each evidenced absence class, should the value remain NO_MESSAGE/MISSING/UNKNOWN, become an explicitly approved zero, or exclude the contract?",
       ("PRESERVE_FOUR_STATE_MISSINGNESS", "EVIDENCE_SCOPED_ZERO_RULE", "FAIL_CLOSED_EXCLUSION"),
       ("NO_ROW_EQUALS_ZERO", "SILENT_IMPUTATION", "COLLAPSE_UNKNOWN_TO_NO_MESSAGE"),
       "Zero imputation can fabricate OI and GEX that was not causally observed.", ("provider non-reporting ambiguity", "coverage loss"),
       ("typed missingness representation and policy gate",), ("each of four states", "no-row never silently zero", "unknown coverage fails closed"),
       "APPROVED_OI_MISSINGNESS", ("B04 and B05 promoted", "coverage evidence", "human approval", "tests pass"), external=True),
    _d("B07", "SPX_ACCOUNT_ACQUISITION", "spx_historical_spot", "ERROR/TRANSPORT_ERROR/UNRESOLVED", "FOUNDATIONAL_BLOCKER", (), ("B08", "B09", "B10"), (REF_ACCOUNT, REF_5A),
       ("P8 produced ERROR/TRANSPORT_ERROR/UNRESOLVED", "Options entitlement does not imply Indices entitlement"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("separately authorized minimal account-specific observation that distinguishes AVAILABLE, DENIED, TRANSPORT_ERROR, EMPTY and SCHEMA_ERROR",), DecisionRequirement.EVIDENCE_FIRST,
       "What is the account-specific SPX index acquisition outcome under one controlled authorized request?",
       ("CLASSIFY_AVAILABLE", "CLASSIFY_DENIED", "CLASSIFY_TRANSPORT_ERROR", "CLASSIFY_EMPTY", "CLASSIFY_SCHEMA_ERROR"),
       ("INFER_AVAILABLE_FROM_OPTIONS", "INFER_DENIED_FROM_TRANSPORT_ERROR", "REPEAT_PROBE_WITHOUT_AUTHORIZATION"),
       "Misclassifying acquisition can cause use of absent or unauthorized data.", ("transient transport ambiguity", "single observation has limited depth"),
       ("no runtime implementation until acquisition is classified",), ("classification fixtures remain mutually exclusive", "raw evidence schema validation"),
       "ACCOUNT_ACQUISITION_CLASSIFIED", ("future authorization", "minimal retained result", "human review"), reprobe=True, external=True, runtime=False, status=DocketStatus.ACCOUNT_VERIFICATION_REQUIRED),
    _d("B08", "SPX_AVAILABLE_TIME", "spx_historical_spot", "BLOCKED_UNRESOLVED", "FOUNDATIONAL_BLOCKER", ("B07",), ("B09", "B10", "B11"), (REF_PROVIDER, REF_5A),
       ("Cboe Global Indices Feed exchange timestamp is represented", "Cboe and OPRA are separate feeds without shared sequence", "no client availability bound is demonstrated"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("client receipt/availability timestamp or deterministic maximum bound",), DecisionRequirement.UPSTREAM_FIRST,
       "After B07, which evidence-backed rule establishes when an SPX print was client-available?",
       ("PROVIDER_SUPPLIED_AVAILABILITY_TIME", "DETERMINISTIC_LATENCY_UPPER_BOUND", "CONSERVATIVE_APPROVED_TRANSFORM", "EXCLUSION"),
       ("EVENT_TIME_EQUALS_AVAILABLE_TIME", "SHARED_OPRA_SEQUENCE", "AVERAGE_LATENCY", "FUTURE_PRINT"),
       "Exchange time can precede the client's knowledge of the separate feed.", ("independent clock domains", "tail latency", "coverage loss"),
       ("versioned SPX as-of selector",), ("future print rejection", "late arrival", "clock/bound boundaries"),
       "CAUSAL_SPX_TIME", ("B07 classified AVAILABLE", "availability evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B09", "SPX_STALENESS_POLICY", "spx_historical_spot", "NO_THRESHOLD_APPROVED", "UPSTREAM_BLOCKER", ("B07", "B08"), ("B11",), (REF_PROVIDER, REF_5A),
       ("no maximum SPX age is approved", "SPX may not print while unchanged"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("empirical cadence, unchanged intervals, gaps, outages and session regimes",), DecisionRequirement.UPSTREAM_FIRST,
       "How is unchanged-but-current distinguished from missing/gapped and stale, and what maximum SPX age is approved?",
       ("EVIDENCE_BACKED_STATE_CLASSIFIER_AND_THRESHOLD", "FAIL_CLOSED_NO_REUSE"),
       ("INVENTED_THRESHOLD", "NO_PRINT_EQUALS_STALE", "NO_PRINT_EQUALS_UNCHANGED", "QUOTE_AGE_AS_SPX_AGE"),
       "An old index value can be treated as contemporaneous or a valid unchanged interval can be discarded.", ("state-classification error", "threshold model risk"),
       ("SPX-specific state and age gate",), ("unchanged/missing/stale fixtures", "at/beyond-boundary", "no threshold blocks"),
       "APPROVED_SPX_STALENESS", ("B07/B08 promoted", "empirical evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B10", "SPX_MISSINGNESS_GAP_POLICY", "spx_historical_spot", "BLOCKED_UNRESOLVED", "UPSTREAM_BLOCKER", ("B07", "B08"), ("B11",), (REF_PROVIDER, REF_5A),
       ("no gap or coverage flags are demonstrated", "unchanged value and no print are not equivalent to a proved feed gap"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("coverage/gap semantics for missing seconds, session gaps and interruptions",), DecisionRequirement.UPSTREAM_FIRST,
       "What evidenced state and action apply to missing seconds, session gaps, feed interruption, unchanged value and no print?",
       ("TYPED_GAP_CLASSIFICATION", "BOUNDED_APPROVED_HOLD", "FAIL_CLOSED_EXCLUSION"),
       ("SILENT_FORWARD_FILL", "NO_PRINT_AUTOMATICALLY_UNCHANGED", "PROXY_FALLBACK_WITHOUT_APPROVAL"),
       "Silent fill can carry later knowledge or conceal an outage.", ("coverage flags may remain unavailable", "exclusion reduces sessions"),
       ("typed missingness/gap gate with provenance",), ("all five cases", "unknown fails closed", "no silent fill"),
       "APPROVED_SPX_GAP_POLICY", ("B07/B08 promoted", "gap evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B11", "CROSS_FEED_ALIGNMENT_POLICY", "cross_feed_temporal_alignment", "BLOCKED_UNRESOLVED", "UPSTREAM_BLOCKER", ("B01", "B03", "B08", "B09", "B10"), (), (REF_CAUSAL, REF_5A),
       ("LAST_CAUSALLY_AVAILABLE is representable", "OPRA and Cboe have no shared sequence", "event_time_skew and available_time_skew are distinct"), EvidenceStatus.PERSISTED_PARTIAL,
       ("both feeds' proven available times", "empirical event-time and available-time skew distributions"), DecisionRequirement.UPSTREAM_FIRST,
       "What separate maximum event-time and available-time skew boundaries permit LAST_CAUSALLY_AVAILABLE alignment?",
       ("LAST_CAUSALLY_AVAILABLE_WITH_APPROVED_DUAL_BOUNDS", "FAIL_CLOSED_UNALIGNED"),
       ("NEAREST_FUTURE", "FUTURE_INTERPOLATION", "FUTURE_BACKFILL", "INVENTED_MAX_SKEW", "EVENT_SKEW_AS_AVAILABLE_SKEW"),
       "Cross-feed pairing may use an input unavailable at T or falsely contemporaneous.", ("clock synchronization error", "asymmetric feed latency", "coverage loss"),
       ("versioned last-causally-available join with two skew checks",), ("future methods rejected", "both skew boundaries", "one stale/missing input blocks"),
       "CAUSAL_CROSS_FEED_ALIGNMENT", ("all upstream time/staleness/gap blockers promoted", "empirical evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B12", "TRADE_ACCOUNT_ACQUISITION", "option_trades", "AMBIGUOUS/EMPTY_SUCCESS", "OPTIONAL_BRANCH_BLOCKER", (), ("B13", "B14"), (REF_ACCOUNT, REF_5A),
       ("P4 returned EMPTY_SUCCESS", "this proves neither denial nor availability"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("authorized minimal non-empty schema observation or explicit denial/entitlement evidence",), DecisionRequirement.EVIDENCE_FIRST,
       "Is trade acquisition AVAILABLE, DENIED, legitimately EMPTY, TRANSPORT_ERROR or SCHEMA_ERROR for this account?",
       ("CLASSIFY_OBSERVED_OUTCOME", "LEAVE_UNRESOLVED_AND_EXCLUDE_TRADE_BRANCH"),
       ("INFER_DENIED", "INFER_AVAILABLE", "REPEAT_PROBE_WITHOUT_AUTHORIZATION"),
       "A false availability conclusion enables an unsupported dealer-flow branch.", ("sample may be legitimately empty", "account state may change"),
       ("none until classification",), ("mutually exclusive classifications", "retained raw/schema evidence"),
       "ACCOUNT_TRADE_ACQUISITION_CLASSIFIED", ("future authorization", "minimal evidence", "human review"), reprobe=True, external=True, runtime=False, status=DocketStatus.ACCOUNT_VERIFICATION_REQUIRED),
    _d("B13", "TRADE_CORRECTION_CANCEL_POLICY", "option_trades", "BLOCKED_UNRESOLVED", "OPTIONAL_BRANCH_BLOCKER", ("B12",), (), (REF_PROVIDER, REF_5A),
       ("exchange timestamp and signed 32-bit wrapping non-global sequence exist", "late/cancel/correction condition codes exist", "cancel is not linked to its original"), EvidenceStatus.PERSISTED_PARTIAL,
       ("deterministic linkage semantics, if any", "provider ordering/revision behavior"), DecisionRequirement.UPSTREAM_FIRST,
       "Which records can be reconstructed without invented linkage, and must unlinked trade-dependent features remain non-reproducible?",
       ("RECONSTRUCT_ONLY_PROVABLY_LINKED", "EXCLUDE_UNRESOLVED_RECORDS", "DECLARE_TRADE_FEATURES_NON_REPRODUCIBLE"),
       ("INVENT_CANCEL_LINKAGE", "GLOBAL_SEQUENCE_ASSUMPTION", "LATEST_TAPE_IS_POINT_IN_TIME"),
       "Retrospective cancels/corrections or guessed links alter the tape known at T.", ("unlinked records", "sequence wrap collisions", "trade-feature incompleteness"),
       ("wrap-aware point-in-time tape state or explicit non-reproducibility gate",), ("wrap/duplicate/late/cancel/correction", "unlinked record fails closed", "repeatability"),
       "CAUSAL_TRADE_CORRECTIONS_OR_EXCLUDED_BRANCH", ("B12 AVAILABLE", "semantics evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B14", "TRADE_CAUSAL_AVAILABILITY", "option_trades", "BLOCKED_UNRESOLVED", "OPTIONAL_BRANCH_BLOCKER", ("B12",), (), (REF_PROVIDER, REF_5A),
       ("historical tape is not evidence of received-by-T", "receipt time and deterministic latency bound are absent"), EvidenceStatus.PERSISTED_INSUFFICIENT,
       ("receipt/availability timestamps or defensible maximum latency evidence",), DecisionRequirement.UPSTREAM_FIRST,
       "Which evidence-backed rule establishes trade availability by replay time?",
       ("PROVIDER_SUPPLIED_AVAILABILITY_TIME", "DETERMINISTIC_LATENCY_UPPER_BOUND", "CONSERVATIVE_APPROVED_TRANSFORM", "EXCLUDE_TRADE_BRANCH"),
       ("EXCHANGE_TIME_EQUALS_AVAILABLE_TIME", "AVERAGE_LATENCY", "HISTORICAL_TAPE_PRESENCE"),
       "Trades arriving after T can affect reconstructed flow at T.", ("tail latency", "excluded trades alter flow"),
       ("point-in-time availability gate",), ("late arrival and bound boundary", "missing availability rejected"),
       "CAUSAL_TRADE_TIME_OR_EXCLUDED_BRANCH", ("B12 AVAILABLE", "availability evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B15", "RATE_CAUSAL_SELECTION_POLICY", "interest_rate", "BLOCKED_HUMAN_DECISION", "FOUNDATIONAL_BLOCKER", (), (), (REF_CAUSAL, REF_ACCOUNT, REF_5A),
       ("rate acquisition is VERIFIED_AVAILABLE", "publication_time is explicit", "SOFR for D published D+1 is not causal intraday D"), EvidenceStatus.PERSISTED_SUFFICIENT,
       (), DecisionRequirement.HUMAN_REQUIRED,
       "Which versioned causal rate policy is approved for replay?",
       ("LAST_CAUSALLY_PUBLISHED_RATE", "FIXED_VERSIONED_RATE", "ANOTHER_EXPLICITLY_APPROVED_CAUSAL_SOURCE_POLICY"),
       ("SAME_DATE_SOFR_BEFORE_PUBLICATION", "NEAREST_FUTURE_PUBLICATION", "UNVERSIONED_FIXED_RATE"),
       "Using a D+1 publication on D is direct look-ahead.",
       ("last-published: stale benchmark risk", "fixed: regime/model risk", "other source: source-specific availability and revision risk"),
       ("last-published: as-of publication selector", "fixed: versioned constant/provenance", "other: approved source-specific selector"),
       ("all: D+1 exclusion and provenance", "last-published: weekends/holidays/missing publication", "fixed: exact version/value", "other: source-specific causal boundaries"),
       "CAUSAL_RATE", ("human selects one class", "class-specific implementation", "class-specific tests pass"), status=DocketStatus.EVIDENCE_SUFFICIENT_DECISION_PENDING),
    _d("B16", "DIVIDEND_POLICY", "dividend_policy", "BLOCKED_HUMAN_DECISION", "FOUNDATIONAL_BLOCKER", (), (), ("src/bot_spx/local_greeks.py", REF_5A),
       ("LOCAL_SPX_BS_V1 requires dividend yield", "ZERO is mathematical/test-only and not approved for real replay"), EvidenceStatus.PERSISTED_SUFFICIENT,
       ("historical causal evidence if a historical source is proposed",), DecisionRequirement.HUMAN_REQUIRED,
       "Which explicit, versioned dividend assumption/source is approved for real replay and which model risk is accepted?",
       ("ZERO_DIVIDEND", "FIXED_VERSIONED_DIVIDEND_YIELD", "HISTORICAL_CAUSAL_DIVIDEND_SOURCE", "ANOTHER_EXPLICIT_MODEL_ASSUMPTION"),
       ("TEST_ZERO_AUTOMATICALLY_PROMOTED", "UNVERSIONED_ASSUMPTION", "FUTURE_DIVIDEND_INFORMATION"),
       "Future-known dividends or revised yields alter IV and every Greek.",
       ("each option changes IV, Delta, Gamma, Theta and Rho", "all changes propagate into downstream GEX", "zero/fixed assumptions create model bias", "historical source adds publication/revision risk"),
       ("policy-bound dividend input with version/provenance",), ("unapproved policy rejected", "version/provenance", "IV/Delta/Gamma/Theta/Rho sensitivity", "GEX propagation"),
       "CAUSAL_DIVIDEND", ("human selects one class", "external evidence when class requires it", "implementation and tests pass"), status=DocketStatus.EVIDENCE_SUFFICIENT_DECISION_PENDING),
    _d("B17", "CONTRACT_METADATA_POLICY", "contract_metadata", "BLOCKED_UNRESOLVED", "FOUNDATIONAL_BLOCKER", ("B18",), (), (REF_PROVIDER, REF_ACCOUNT, REF_5A),
       ("root, expiration, strike, right and symbol were observed", "expiration date equals replay date under the conservative 0DTE rule", "expiration time, settlement style, identity availability/reference time and full provenance remain unresolved"), EvidenceStatus.PERSISTED_PARTIAL,
       ("historical expiration/settlement and stable identity evidence", "reference_time, available_time and provenance", "holiday/special listing evidence"), DecisionRequirement.UPSTREAM_FIRST,
       "Which ordinary-date fields may be conservatively derived, and which historical/special cases must require authoritative metadata or exclusion?",
       ("VERSIONED_ORDINARY_DERIVATION_WITH_SPECIAL_FAIL_CLOSED", "AUTHORITATIVE_HISTORICAL_METADATA_ONLY"),
       ("CURRENT_METADATA_APPLIED_HISTORICALLY", "ASSUME_SPECIAL_LISTING", "INFER_SETTLEMENT_OR_EXPIRATION_TIME_SILENTLY"),
       "Later/current metadata can leak historical contract facts.", ("inactive contract survivorship", "special-listing exclusion", "identity collision"),
       ("versioned metadata resolver after policy approval",), ("all required fields", "ordinary/special/unknown", "reference/available-time boundaries", "identity determinism"),
       "CAUSAL_CONTRACT_METADATA", ("B18 promoted", "historical evidence", "human approval", "tests pass"), external=True, status=DocketStatus.BLOCKED_UPSTREAM),
    _d("B18", "SESSION_CALENDAR_EXPIRATION_POLICY", "session_calendar_expiration", "BLOCKED_UNRESOLVED", "FOUNDATIONAL_BLOCKER", (), ("B17",), (REF_5A,),
       ("America/New_York and expiration date=replay date are necessary", "holiday, early close, special expiration and historical listing changes remain unresolved"), EvidenceStatus.PERSISTED_PARTIAL,
       ("versioned historical sessions/listings/expiration rules",), DecisionRequirement.EVIDENCE_FIRST,
       "Which historical calendar source and rules define trading date, regular session, DST, early close, holiday, SPXW PM settlement, expiration time and special expiration?",
       ("VERSIONED_HISTORICAL_CALENDAR_AND_LISTING_RULES", "EXCLUDE_UNVERIFIED_SPECIAL_DATES"),
       ("CURRENT_CALENDAR_ASSUMED_HISTORICAL", "FIXED_UTC_OFFSET", "REGULAR_CLOSE_ON_EARLY_CLOSE", "SPX_AND_SPXW_SETTLEMENT_CONFLATION"),
       "Wrong historical session or expiry boundaries admit post-close/post-expiry facts.", ("historical rule changes", "special-date coverage loss"),
       ("no calendar engine in 5B; later versioned resolver",), ("America/New_York DST", "holidays/early closes", "PM settlement and expiration", "historical changes/specials fail closed"),
       "APPROVED_HISTORICAL_SESSION_CALENDAR", ("historical source evidence", "human approval", "later implementation and tests"), external=True),
    _d("B19", "HISTORICAL_DEPTH_REQUIREMENT", "historical_depth", "HUMAN_DECISION_PENDING", "DOWNSTREAM_BLOCKER", (), (), (REF_ACCOUNT, REF_5A),
       ("all account-verified depth is SINGLE_DATE_ONLY", "no minimum backtest length decision is persisted"), EvidenceStatus.PERSISTED_SUFFICIENT,
       ("account component coverage after the required depth is defined",), DecisionRequirement.HUMAN_REQUIRED,
       "What minimum sessions, date span, market regimes, per-component availability, and continuous-versus-sampled coverage define sufficient depth?",
       ("EXPLICIT_VERSIONED_DEPTH_REQUIREMENT", "EXPLICIT_VERSIONED_SAMPLED_PERIOD_REQUIREMENT"),
       ("INVENTED_SESSION_COUNT", "SINGLE_DATE_PROMOTION", "PROVIDER_DESCRIBED_EQUALS_ACCOUNT_VERIFIED"),
       "Selecting dates after observing results or silently accepting gaps biases evaluation.", ("regime underrepresentation", "component coverage mismatch", "sampling bias"),
       ("offline depth manifest only after approval and authorization",), ("minimum/date boundaries", "regime declaration", "component holes", "continuous/sample conformance"),
       "SUFFICIENT_ACCOUNT_VERIFIED_DEPTH", ("human depth decision", "later separately authorized evidence", "manifest validation"), external=True, runtime=False, status=DocketStatus.EVIDENCE_SUFFICIENT_DECISION_PENDING),
)


DOCKET_BY_ID = MappingProxyType({item.blocker_id: item for item in DOCKETS})


DECISION_PACKETS = (
    HumanDecisionPacket("Q1", ("B01", "B02", "B03"), "Which availability, correction and quote-age policies make quotes causal?", "Quotes feed local IV and cross-feed joins.", ("NBBO/event time; acquisition verified; missing sequence/receipt and correction semantics",), ("availability bound", "correction semantics", "cadence/latency coverage"), ("evidence-backed availability", "condition-aware as-of policy", "approved age gate", "exclude"), ("event=available", "latest-row-wins", "invented age", "future values"), ("quotes", "local IV/Greeks", "GEX"), ("latency tails", "correction ambiguity", "coverage loss"), True, True, True),
    HumanDecisionPacket("Q2", ("B04", "B05", "B06"), "Which OI availability, correction and four-state missingness policies are approved?", "OI walls/static GEX require causal, typed OI.", ("previous-day OI; daily message; multiple rows; no flag",), ("receipt/bound", "replacement semantics", "coverage classification"), ("as-of message policy", "preserve four states", "exclude"), ("message=available", "latest-row-wins", "no-row=zero"), ("walls", "static OI/GEX"), ("unflagged corrections", "missingness ambiguity"), True, True, True),
    HumanDecisionPacket("Q3", ("B07", "B08", "B09", "B10"), "After acquisition classification, which SPX availability, state, gap and age policies are approved?", "A causal underlying is mandatory for local IV/Greeks.", ("transport error; exchange timestamp; separate feed; unchanged may not print",), ("acquisition outcome", "receipt/bound", "gap/cadence evidence"), ("classified acquisition plus evidenced as-of/state rules", "exclude"), ("Options implies Indices", "event=available", "silent fill", "invented age"), ("SPX", "alignment", "local IV/Greeks"), ("feed latency", "state error", "coverage loss"), True, True, True),
    HumanDecisionPacket("Q4", ("B03", "B09", "B11"), "Which distinct quote age, SPX age, event skew and availability skew limits are approved?", "Temporal compatibility cannot be inferred from timestamps alone.", ("LAST_CAUSALLY_AVAILABLE representable; future joins prohibited",), ("empirical cadence/latency/outage/skew coverage",), ("separate evidence-backed limits", "fail-closed unaligned"), ("one shared invented limit", "future interpolation/backfill/nearest"), ("aligned local IV inputs",), ("clock/latency model error", "coverage loss"), True, True, True),
    HumanDecisionPacket("Q5", ("B12", "B13", "B14"), "Is the trade branch supportable, and under which point-in-time correction and availability rules?", "Dealer flow/aggressor/dynamic GEX require trades.", ("empty success; wrapping sequence; unlinked codes; no receipt time",), ("acquisition classification", "linkage/ordering", "availability bound"), ("causal reconstructable subset", "exclude unresolved records", "declare branch non-reproducible"), ("infer entitlement", "invent links", "exchange=available"), ("dealer flow", "aggressor classification", "dynamic GEX"), ("incomplete tape", "unlinked cancels", "latency"), True, True, True),
    HumanDecisionPacket("Q6", ("B15",), "Which causal rate policy is approved?", "Black-Scholes requires a rate.", ("publication time; D rate published D+1",), (), ("last causally published", "fixed versioned", "other approved causal policy"), ("same-day before publication", "unversioned rate"), ("local IV and Greeks",), ("staleness/model/source risk"), True, False, True),
    HumanDecisionPacket("Q7", ("B16",), "Which versioned dividend policy and model risk are approved?", "Black-Scholes requires dividend yield.", ("ZERO is test-only",), ("causal history only if selected",), ("zero", "fixed versioned", "historical causal", "other explicit assumption"), ("automatic test-zero promotion", "future information"), ("IV", "all Greeks", "GEX"), ("model/publication risk"), True, False, True),
    HumanDecisionPacket("Q8", ("B17", "B18"), "Which historical metadata/calendar rules and fail-closed exceptions are approved?", "Contract identity and time-to-expiry require historical rules.", ("partial fields; NY timezone; date=D rule",), ("historical session/listing/settlement evidence",), ("versioned historical rules", "exclude specials"), ("current calendar historically", "assume settlement/time"), ("universe", "time to expiry", "local IV/Greeks"), ("historical change", "survivorship"), True, True, True),
    HumanDecisionPacket("Q9", ("B19",), "What versioned minimum historical depth is required?", "Sufficiency cannot be assessed without a target.", ("SINGLE_DATE_ONLY",), ("account coverage after target definition",), ("explicit sessions/span/regimes/components/continuity",), ("invented number", "single date sufficient"), ("future backtest readiness only",), ("sampling/regime risk"), True, True, True),
)


MINIMIZATION_PRINCIPLE = MappingProxyType({
    "minimum_calls": True, "minimum_rows": True, "minimum_dates": True,
    "minimum_retention": True, "bulk": False, "crawler": False,
    "pagination": "SEPARATE_AUTHORIZATION_REQUIRED",
    "reason": "P2 ACQUISITION_SCOPE_ANOMALY returned 17326 rows",
})


EVIDENCE_REQUESTS = (
    EvidenceRequest("E01", ("B01", "B02", "B03"), "Quote availability, correction/condition and cadence semantics", ("one already-known contract", "one date", "minimum records covering only required cases", "no pagination"), "PERSISTED_PROVIDER_ARTIFACT_OR_SEPARATELY_AUTHORIZED_ACCOUNT_EVIDENCE", True, True, True, "retain minimum raw response plus request context and hashes", ("availability timestamp", "deterministic bound", "semantics proved", "semantics absent"), ("question answered", "scope expands", "unexpected row volume", "pagination needed")),
    EvidenceRequest("E02", ("B04", "B05", "B06"), "OI availability, replacement and missingness coverage semantics", ("minimum messages/contracts/dates needed to distinguish cases", "no bulk", "no pagination"), "PERSISTED_PROVIDER_ARTIFACT_OR_SEPARATELY_AUTHORIZED_ACCOUNT_EVIDENCE", True, True, True, "retain minimum raw messages and provenance", ("semantics proved", "partial", "not exposed"), ("question answered", "scope anomaly", "pagination needed")),
    EvidenceRequest("E03", ("B07",), "Account-specific SPX acquisition classification", ("one authorized request", "one date", "minimum rows", "no retry unless separately authorized"), "ACCOUNT_OBSERVATION", True, True, True, "retain exact minimal response/error and context", ("AVAILABLE", "DENIED", "TRANSPORT_ERROR", "EMPTY", "SCHEMA_ERROR"), ("first classifiable outcome", "unexpected volume", "credential/access issue")),
    EvidenceRequest("E04", ("B08", "B09", "B10", "B11"), "SPX availability, unchanged/gap/cadence and skew facts", ("only after B07 AVAILABLE", "minimum date/window", "minimum rows", "no pagination"), "ACCOUNT_AND_PROVIDER_SEMANTICS", True, True, True, "retain minimum raw observations and timing provenance", ("facts proved", "partial", "not exposed"), ("B07 not AVAILABLE", "question answered", "scope anomaly", "pagination needed")),
    EvidenceRequest("E05", ("B12",), "Trade account acquisition classification", ("one authorized minimally likely non-empty contract/window", "minimum rows", "no retry/pagination"), "ACCOUNT_OBSERVATION", True, True, True, "retain exact minimal response/error and context", ("AVAILABLE", "DENIED", "LEGITIMATELY_EMPTY", "TRANSPORT_ERROR", "SCHEMA_ERROR"), ("first classifiable outcome", "unexpected volume", "pagination needed")),
    EvidenceRequest("E06", ("B13", "B14"), "Trade linkage/ordering and availability semantics", ("only after B12 AVAILABLE", "minimum records covering target conditions", "no bulk/pagination"), "PERSISTED_PROVIDER_ARTIFACT_OR_SEPARATELY_AUTHORIZED_ACCOUNT_EVIDENCE", True, True, True, "retain minimum raw records and provenance", ("causal semantics proved", "unlinked remains", "availability absent"), ("B12 not AVAILABLE", "question answered", "scope anomaly")),
    EvidenceRequest("E07", ("B17", "B18"), "Historical contract/session/settlement/listing facts", ("ordinary plus minimum exceptional dates needed by approved scope", "no broad crawl"), "VERSIONED_HISTORICAL_REFERENCE_EVIDENCE", True, False, True, "retain cited/versioned extracts and provenance only", ("rules evidenced", "special cases excluded", "insufficient"), ("approved scope covered", "bulk needed", "unversioned source")),
    EvidenceRequest("E08", ("B19",), "Account coverage against an already-approved depth requirement", ("only dates/components required by Q9", "start with boundary samples", "no bulk/pagination"), "ACCOUNT_OBSERVATION", True, True, True, "retain coverage manifest and minimum boundary evidence", ("sufficient", "insufficient", "component-specific gap"), ("Q9 pending", "gap found", "unexpected volume", "pagination needed")),
)


RESOLUTION_EDGES = tuple(
    ResolutionEdge(a, b) for a, b in (
        ("B01", "B02"), ("B01", "B03"), ("B01", "B11"), ("B03", "B11"),
        ("B04", "B05"), ("B04", "B06"), ("B05", "B06"),
        ("B07", "B08"), ("B07", "B09"), ("B07", "B10"),
        ("B08", "B09"), ("B08", "B10"), ("B08", "B11"),
        ("B09", "B11"), ("B10", "B11"),
        ("B12", "B13"), ("B12", "B14"), ("B18", "B17"),
    )
)


RESOLUTION_CLASSIFICATION = MappingProxyType({
    "without_external_evidence": ("B15", "B16"),
    "with_human_decision": tuple(f"B{i:02d}" for i in range(1, 20)),
    "only_after_external_evidence": ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12", "B13", "B14", "B17", "B18", "B19"),
    "only_after_another_blocker": ("B02", "B03", "B05", "B06", "B08", "B09", "B10", "B11", "B13", "B14", "B17"),
})


TRADE_FEATURE_DERIVATION = MappingProxyType({
    "without_trades": ("SPX spot", "Call Wall", "Put Wall", "Gamma Flip / Zero Gamma", "Static OI/GEX", "quote-based local IV", "local Greeks"),
    "trades_required": ("Dealer flow", "aggressor classification", "Dynamic GEX", "Dealer Dynamic GEX"),
    "possible_no_dealer_flow_branch_not_approved": ("Gamma Balance", "Gamma Regime", "Mean Reversion signal", "Breakout/Breakdown signal", "Risk gate", "Entry permission"),
    "semantic_changes_if_trade_branch_omitted": ("no dealer-flow estimate", "no aggressor classification", "no dynamic/dealer GEX contribution", "signals become static-OI/level semantics rather than dealer-flow-aware semantics"),
    "operational_degraded_mode_created": False,
})


LOCAL_GREEKS_DEPENDENCY_CHAIN = MappingProxyType({
    "eligible_local_iv_requires": ("causal quote", "causal SPX", "causal rate", "approved dividend", "causal metadata", "approved alignment", "approved staleness"),
    "eligible_local_greeks_requires": ("eligible local IV", "LOCAL_SPX_BS_V1"),
    "currently_eligible_inputs": (),
    "provider_greeks_iv": "EXCLUDED",
    "local_greeks_iv": "NEEDS_RECONSTRUCTION",
})


NEXT_ACTIONS = (
    NextAction("A01", ActionClass.CONTROLLED_EVIDENCE_ACQUISITION, ("B01", "B02", "B03"), (), "Execute E01 only after future authorization."),
    NextAction("A02", ActionClass.CONTROLLED_EVIDENCE_ACQUISITION, ("B04", "B05", "B06"), (), "Execute E02 only after future authorization."),
    NextAction("A03", ActionClass.CONTROLLED_EVIDENCE_ACQUISITION, ("B07",), (), "Execute E03 only after future authorization."),
    NextAction("A04", ActionClass.CONTROLLED_EVIDENCE_ACQUISITION, ("B12",), (), "Execute E05 only after future authorization."),
    NextAction("A05", ActionClass.HUMAN_DECISION, ("B15",), (), "Resolve Q6 from persisted evidence."),
    NextAction("A06", ActionClass.HUMAN_DECISION, ("B16",), (), "Resolve Q7; acquire evidence later only if the chosen class needs it."),
    NextAction("A07", ActionClass.HUMAN_DECISION, ("B19",), (), "Define Q9 before any depth acquisition."),
    NextAction("A08", ActionClass.CONTROLLED_EVIDENCE_ACQUISITION, ("B18",), (), "Execute E07 only after future authorization."),
    NextAction("A09", ActionClass.BLOCKED_UPSTREAM, ("B08", "B09", "B10", "B11"), ("A03",), "Acquire/decide SPX temporal facts only if B07 becomes AVAILABLE."),
    NextAction("A10", ActionClass.BLOCKED_UPSTREAM, ("B13", "B14"), ("A04",), "Acquire/decide trade tape facts only if B12 becomes AVAILABLE."),
    NextAction("A11", ActionClass.OFFLINE_IMPLEMENTATION, tuple(f"B{i:02d}" for i in range(1, 20)), ("A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10"), "Implement only policies later approved and only after their evidence gates."),
    NextAction("A12", ActionClass.VALIDATION, tuple(f"B{i:02d}" for i in range(1, 20)), ("A11",), "Run required blocker-specific fail-closed tests before any promotion."),
)


FROZEN_INPUTS = MappingProxyType({
    "current_session_status": CURRENT_SESSION_STATUS, "current_blockers": CURRENT_BLOCKER_COUNT,
    "provider_greeks_iv": "EXCLUDED", "local_greeks_iv": "NEEDS_RECONSTRUCTION",
    "SPX": "BLOCKED_UNRESOLVED", "OI": "BLOCKED_UNRESOLVED",
    "trades": "BLOCKED_UNRESOLVED", "quotes": "BLOCKED_UNRESOLVED",
    "historical_spxw_0dte_universe": "READY_WITH_CONSERVATIVE_RULE/LOW",
    "mapping_promotions": MAPPING_PROMOTIONS, "cutover": CUTOVER,
    "available_capabilities": 7, "trade_acquisition": "AMBIGUOUS/EMPTY_SUCCESS",
    "spx_acquisition": "ERROR/TRANSPORT_ERROR/UNRESOLVED",
    "historical_depth": "SINGLE_DATE_ONLY", "account_tier": "NOT_PERSISTED/UNRESOLVED",
    "P2": "ACQUISITION_SCOPE_ANOMALY", "P2_row_count": 17_326,
})


def validate_resolution_dag(edges: Iterable[ResolutionEdge] = RESOLUTION_EDGES) -> tuple[str, ...]:
    """Validate known blocker IDs and return a deterministic topological order."""
    items = tuple(edges)
    known = set(DOCKET_BY_ID)
    endpoints = {node for edge in items for node in (edge.prerequisite, edge.dependent)}
    unknown = sorted(endpoints - known)
    if unknown:
        raise ValueError(f"unknown blocker IDs: {unknown}")
    incoming = {node: 0 for node in known}
    outgoing = {node: [] for node in known}
    for edge in items:
        outgoing[edge.prerequisite].append(edge.dependent)
        incoming[edge.dependent] += 1
    ready = sorted(node for node, count in incoming.items() if count == 0)
    ordered: list[str] = []
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for dependent in sorted(outgoing[node]):
            incoming[dependent] -= 1
            if incoming[dependent] == 0:
                ready.append(dependent)
                ready.sort()
    if len(ordered) != len(known):
        raise ValueError("resolution DAG contains a cycle")
    return tuple(ordered)


def contract_dict() -> dict[str, object]:
    """Return JSON-compatible primitives without weakening immutable constants."""
    def encode(value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, tuple):
            return [encode(item) for item in value]
        if isinstance(value, (dict, MappingProxyType)):
            return {key: encode(item) for key, item in value.items()}
        if hasattr(value, "__dataclass_fields__"):
            return encode(asdict(value))
        return value

    return {
        "schema_version": "1.0", "phase": SPEC_VERSION, "source_phase": SOURCE_PHASE,
        "frozen_inputs": encode(FROZEN_INPUTS), "dockets": encode(DOCKETS),
        "decision_packets": encode(DECISION_PACKETS), "evidence_requests": encode(EVIDENCE_REQUESTS),
        "minimization_principle": encode(MINIMIZATION_PRINCIPLE),
        "resolution_edges": encode(RESOLUTION_EDGES),
        "resolution_topological_order": list(validate_resolution_dag()),
        "resolution_classification": encode(RESOLUTION_CLASSIFICATION),
        "trade_feature_derivation": encode(TRADE_FEATURE_DERIVATION),
        "local_greeks_dependency_chain": encode(LOCAL_GREEKS_DEPENDENCY_CHAIN),
        "next_actions": encode(NEXT_ACTIONS),
        "phase_actions_executed": [], "policies_approved": [],
    }
