"""Offline, fail-closed review of written provider evidence.

This module deliberately has no network, persistence, provider-loader, or
mapping-application capability.  Its only output is evidence for a later,
separate human decision.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
import json
import re
from types import MappingProxyType
from typing import Iterable, Mapping


EXPECTED_PROVIDER = "ThetaData"


class EvidenceClass(str, Enum):
    DOCUMENTED = "DOCUMENTED"
    PROVIDER_WRITTEN_CONFIRMATION = "PROVIDER_WRITTEN_CONFIRMATION"
    INFERRED = "INFERRED"
    CONTRADICTORY = "CONTRADICTORY"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNASSESSED = "UNASSESSED"


class ProposalStatus(str, Enum):
    READY = "READY"
    READY_WITH_CONSERVATIVE_RULE = "READY_WITH_CONSERVATIVE_RULE"
    NEEDS_RECONSTRUCTION = "NEEDS_RECONSTRUCTION"
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    EXCLUDED = "EXCLUDED"


class OverallReviewStatus(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"


@dataclass(frozen=True)
class Question:
    question_id: str
    priority: str
    category: str


_QUESTION_ROWS = (
    ("PIT-01", "P0", "Option trades"), ("PIT-02", "P0", "Option quotes"),
    ("PIT-03", "P0", "Open interest"), ("PIT-04", "P1", "Index data"),
    ("PIT-05", "P1", "Greeks"), ("PIT-06", "P1", "Implied volatility"),
    ("OI-01", "P0", "OI meaning"), ("OI-02", "P0", "OI reference date"),
    ("OI-03", "P0", "OI publication time"), ("OI-04", "P0", "OI pre-open guarantee"),
    ("OI-05", "P1", "Late/missing OI"), ("OI-06", "P0", "OI corrections"),
    ("OI-07", "P0", "OI historical response"), ("OI-08", "P0", "OI revision timestamp"),
    ("OI-09", "P0", "OI as-of reconstruction"), ("TRD-01", "P0", "Trade timestamp"),
    ("TRD-02", "P1", "Trade sequence"), ("TRD-03", "P1", "Trade lifecycle"),
    ("TRD-04", "P2", "Trade delivery anomalies"), ("TRD-05", "P0", "Trade as-of stream"),
    ("QTE-01", "P0", "Quote timestamp"), ("QTE-02", "P1", "Quote sequence/order"),
    ("QTE-03", "P1", "Quote meaning"), ("QTE-04", "P2", "Locked/crossed quotes"),
    ("QTE-05", "P0", "Quote/NBBO as-of stream"), ("TIM-01", "P0", "Clock inventory"),
    ("TIM-02", "P0", "Availability guarantee"), ("IDX-01", "P1", "Index timestamp/source"),
    ("IDX-02", "P1", "Index resolution/depth"), ("IDX-03", "P1", "Index revisions/PIT"),
    ("IDX-04", "P2", "Index/OPRA synchronization"), ("GRK-01", "P1", "Greek/IV availability"),
    ("GRK-02", "P1", "Stored vs recalculated"), ("GRK-03", "P1", "Model version/conventions"),
    ("GRK-04", "P0", "Input timing"), ("GRK-05", "P1", "Historical identity"),
    ("SYM-01", "P1", "SPX/SPXW identity"), ("SYM-02", "P1", "Contract metadata"),
    ("SYM-03", "P1", "Historical 0DTE selection"), ("ENT-01", "P1", "Required entitlements"),
    ("ENT-02", "P1", "Depth/resolution entitlements"),
)
QUESTION_REGISTRY: Mapping[str, Question] = MappingProxyType(
    {qid: Question(qid, priority, category) for qid, priority, category in _QUESTION_ROWS}
)


@dataclass(frozen=True)
class SourceFragment:
    fragment_id: str
    text: str


@dataclass(frozen=True)
class ProviderEvidenceRecord:
    question_id: str
    provider: str
    category: str
    received_at: datetime
    support_channel: str
    support_reference: str
    raw_response: bytes
    verbatim_summary: str
    interpretation: str
    source_documents: tuple[str, ...]
    source_fragments: tuple[SourceFragment, ...]
    evidence_class: EvidenceClass
    confidence: Confidence
    affected_fields: tuple[str, ...]
    mapping_before: str
    proposed_mapping_after: ProposalStatus
    temporal_rule: str
    correction_rule: str
    remaining_ambiguity: str
    semantic_dimensions: tuple[str, ...] = ()
    semantic_claims: tuple[tuple[str, str], ...] = ()
    review_status: str = "PENDING_HUMAN_REVIEW"

    def __post_init__(self) -> None:
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        if self.review_status != "PENDING_HUMAN_REVIEW":
            raise ValueError("evidence starts pending human review")
        if not isinstance(self.raw_response, bytes):
            raise TypeError("raw_response must be immutable bytes")


@dataclass(frozen=True)
class ProviderQuestionResponse:
    """One question-scoped view; fragments may share one raw paragraph."""

    evidence: ProviderEvidenceRecord


@dataclass(frozen=True)
class ProposedMappingChange:
    field: str
    mapping_before: str
    proposed_mapping_after: ProposalStatus
    supporting_question_ids: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    temporal_rule: str
    correction_rule: str
    confidence: Confidence
    remaining_ambiguity: str
    requires_human_review: bool = True

    def __post_init__(self) -> None:
        if not self.requires_human_review:
            raise ValueError("mapping proposals always require human review")


@dataclass(frozen=True)
class CoverageReport:
    total_questions: int
    answered: int
    unanswered: int
    P0_answered: int
    P0_missing: int
    P1_answered: int
    P1_missing: int
    ambiguous: int
    contradictory: int
    unknown: int
    proposals: int
    blocked_proposals: int


@dataclass(frozen=True)
class ProviderEvidenceReview:
    answered_questions: tuple[str, ...]
    unanswered_questions: tuple[str, ...]
    answered_P0: tuple[str, ...]
    missing_P0: tuple[str, ...]
    documented: tuple[str, ...]
    ambiguous: tuple[str, ...]
    contradictory: tuple[str, ...]
    unknown: tuple[str, ...]
    proposed_changes: tuple[ProposedMappingChange, ...]
    blocked_changes: tuple[ProposedMappingChange, ...]
    overall_review_status: OverallReviewStatus
    coverage: CoverageReport
    human_review_required: bool = True


AMBIGUOUS_TERMS = (
    "approximately", "typically", "usually", "generally", "normally",
    "may", "can", "often", "around", "as available",
)
CRITICAL_DIMENSIONS = frozenset({"available_time", "corrections", "point_in_time"})
OI_REQUIRED = frozenset({"reference_date", "available_time", "delayed_or_missing", "corrections", "point_in_time", "as_of_reconstruction"})
STREAM_REQUIRED = frozenset({"timestamp", "available_time", "corrections", "sequence", "historical_revision"})
GREEK_RECONSTRUCTION_REQUIRED = frozenset({"option_input", "underlying_input", "rate", "dividend", "model_version", "input_timing"})


def ambiguity_terms(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    return tuple(term for term in AMBIGUOUS_TERMS if re.search(rf"\b{re.escape(term)}\b", lowered))


def assess_confidence(*, exact_answer: bool, documentation: bool,
                      timestamp_defined: bool, corrections_defined: bool,
                      point_in_time_defined: bool, text: str) -> Confidence:
    """Explicit assessment; provider authorship is intentionally not an input."""
    if ambiguity_terms(text):
        return Confidence.LOW
    score = sum((exact_answer, documentation, timestamp_defined,
                 corrections_defined, point_in_time_defined))
    return Confidence.HIGH if score == 5 else Confidence.MEDIUM if score >= 3 else Confidence.LOW


def _validated(records: Iterable[ProviderEvidenceRecord], registry: Mapping[str, Question]) -> tuple[ProviderEvidenceRecord, ...]:
    result = []
    seen: set[str] = set()
    for record in records:
        question = registry.get(record.question_id)
        if question is None:
            raise ValueError(f"unknown question_id: {record.question_id}")
        if record.question_id in seen:
            raise ValueError(f"duplicate answer: {record.question_id}")
        if record.provider != EXPECTED_PROVIDER:
            raise ValueError(f"unexpected provider for {record.question_id}")
        if record.category != question.category:
            raise ValueError(f"wrong category for {record.question_id}")
        seen.add(record.question_id)
        result.append(record)
    return tuple(result)


def _classify_contradictions(records: tuple[ProviderEvidenceRecord, ...]) -> tuple[ProviderEvidenceRecord, ...]:
    claims: dict[str, set[str]] = {}
    for record in records:
        for key, value in record.semantic_claims:
            claims.setdefault(key, set()).add(value)
    conflicts = {key for key, values in claims.items() if len(values) > 1}
    return tuple(replace(record, evidence_class=EvidenceClass.CONTRADICTORY)
                 if any(key in conflicts for key, _ in record.semantic_claims) else record
                 for record in records)


def _classify_ambiguities(records: tuple[ProviderEvidenceRecord, ...]) -> tuple[ProviderEvidenceRecord, ...]:
    return tuple(
        replace(record, evidence_class=EvidenceClass.AMBIGUOUS)
        if (ambiguity_terms(record.raw_response.decode("utf-8"))
            and CRITICAL_DIMENSIONS.intersection(record.semantic_dimensions))
        else record
        for record in records
    )


def _is_blocked(record: ProviderEvidenceRecord, missing_p0: tuple[str, ...]) -> bool:
    if record.evidence_class in {EvidenceClass.UNKNOWN, EvidenceClass.AMBIGUOUS, EvidenceClass.CONTRADICTORY}:
        return True
    if ambiguity_terms(record.raw_response.decode("utf-8")) and CRITICAL_DIMENSIONS.intersection(record.semantic_dimensions):
        return True
    if record.evidence_class is EvidenceClass.INFERRED and record.affected_fields:
        return True
    if missing_p0 and record.affected_fields:
        return True
    if record.correction_rule.strip().upper() in {"", "UNKNOWN", "LATEST_REVISED"}:
        return True
    dimensions = frozenset(record.semantic_dimensions)
    field_group = record.question_id.split("-", 1)[0]
    if field_group == "OI" or "open_interest" in record.affected_fields:
        return not OI_REQUIRED <= dimensions
    if field_group in {"TRD", "QTE"}:
        return not STREAM_REQUIRED <= dimensions
    if field_group == "GRK" or set(record.affected_fields) & {"iv", "delta", "gamma", "other_greeks"}:
        if record.proposed_mapping_after is ProposalStatus.NEEDS_RECONSTRUCTION:
            return not GREEK_RECONSTRUCTION_REQUIRED <= dimensions
        return "point_in_time" not in dimensions
    return not {"available_time", "corrections", "point_in_time"} <= dimensions


def review_provider_evidence(
    registry: Mapping[str, Question],
    evidence_records: Iterable[ProviderEvidenceRecord],
    current_mapping_spec: Mapping[str, str],
) -> ProviderEvidenceReview:
    """Review evidence without mutating ``current_mapping_spec`` or applying it."""
    before = dict(current_mapping_spec)
    records = _classify_contradictions(_classify_ambiguities(_validated(evidence_records, registry)))
    answered = tuple(sorted(record.question_id for record in records))
    unanswered = tuple(sorted(set(registry) - set(answered)))
    answered_p0 = tuple(qid for qid in answered if registry[qid].priority == "P0")
    missing_p0 = tuple(qid for qid in unanswered if registry[qid].priority == "P0")
    proposals, blocked = [], []
    for record in sorted(records, key=lambda item: item.question_id):
        if not record.affected_fields:
            continue
        for field in sorted(record.affected_fields):
            proposal = ProposedMappingChange(
                field, current_mapping_spec.get(field, record.mapping_before),
                record.proposed_mapping_after, (record.question_id,),
                tuple(fragment.fragment_id for fragment in record.source_fragments),
                record.temporal_rule, record.correction_rule, record.confidence,
                record.remaining_ambiguity,
            )
            (blocked if _is_blocked(record, missing_p0) else proposals).append(proposal)
    assert dict(current_mapping_spec) == before  # no automatic application
    classes = lambda kind: tuple(r.question_id for r in records if r.evidence_class is kind)
    ambiguous, contradictory, unknown = (classes(EvidenceClass.AMBIGUOUS),
                                         classes(EvidenceClass.CONTRADICTORY),
                                         classes(EvidenceClass.UNKNOWN))
    status = (OverallReviewStatus.INCOMPLETE if unanswered else
              OverallReviewStatus.BLOCKED if blocked or ambiguous or contradictory or unknown else
              OverallReviewStatus.READY_FOR_HUMAN_REVIEW)
    p1_answered = sum(registry[qid].priority == "P1" for qid in answered)
    p1_total = sum(question.priority == "P1" for question in registry.values())
    coverage = CoverageReport(len(registry), len(answered), len(unanswered),
                              len(answered_p0), len(missing_p0), p1_answered,
                              p1_total - p1_answered, len(ambiguous),
                              len(contradictory), len(unknown), len(proposals), len(blocked))
    return ProviderEvidenceReview(
        answered, unanswered, answered_p0, missing_p0,
        classes(EvidenceClass.DOCUMENTED), ambiguous, contradictory, unknown,
        tuple(proposals), tuple(blocked), status, coverage,
    )


def human_review_gate(_: ProviderEvidenceReview) -> bool:
    return True


def deterministic_ledger(review: ProviderEvidenceReview,
                         records: Iterable[ProviderEvidenceRecord]) -> str:
    """Return stable JSON; raw bytes are losslessly represented as hex."""
    proposal_by_question = {qid: proposal.proposed_mapping_after.value
                            for proposal in review.proposed_changes + review.blocked_changes
                            for qid in proposal.supporting_question_ids}
    rows = []
    classified = _classify_contradictions(_classify_ambiguities(tuple(records)))
    for record in sorted(classified, key=lambda item: item.question_id):
        rows.append({
            "question_id": record.question_id,
            "evidence_source": list(record.source_documents),
            "evidence_class": record.evidence_class.value,
            "confidence": record.confidence.value,
            "proposed_change": proposal_by_question.get(record.question_id),
            "review_status": record.review_status,
            "raw_response_hex": record.raw_response.hex(),
        })
    return json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
