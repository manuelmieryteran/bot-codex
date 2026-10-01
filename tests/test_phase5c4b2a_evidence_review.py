from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from bot_spx.provider_evidence_review import (
    Confidence, EvidenceClass, EXPECTED_PROVIDER, GREEK_RECONSTRUCTION_REQUIRED,
    OI_REQUIRED, OverallReviewStatus, ProposalStatus, ProviderEvidenceRecord,
    QUESTION_REGISTRY, STREAM_REQUIRED, SourceFragment, ambiguity_terms,
    assess_confidence, deterministic_ledger, human_review_gate,
    review_provider_evidence,
)


def evidence(qid, *, text="Exact synthetic confirmation.", evidence_class=EvidenceClass.PROVIDER_WRITTEN_CONFIRMATION,
             fields=(), dimensions=("available_time", "corrections", "point_in_time"),
             correction="POINT_IN_TIME", proposal=ProposalStatus.READY, claims=(), fragment="f1"):
    question = QUESTION_REGISTRY.get(qid)
    category = question.category if question else "Unknown"
    return ProviderEvidenceRecord(
        qid, EXPECTED_PROVIDER, category, datetime(2026, 1, 1, tzinfo=timezone.utc),
        "synthetic-test", "SYNTHETIC-NOT-PROVIDER", text.encode(), "Synthetic summary",
        "Synthetic interpretation", ("synthetic fixture",),
        (SourceFragment(fragment, text),), evidence_class, Confidence.MEDIUM,
        tuple(fields), "BLOCKED_UNRESOLVED", proposal, "exact synthetic rule",
        correction, "", tuple(dimensions), tuple(claims),
    )


def complete_records(replacement=None):
    replacement = replacement or {}
    return [replacement.get(qid, evidence(qid, fields=())) for qid in QUESTION_REGISTRY]


def review(records):
    mapping = {"open_interest": "BLOCKED_UNRESOLVED", "bid": "BLOCKED_UNRESOLVED",
               "trade_price": "BLOCKED_UNRESOLVED", "gamma": "NEEDS_RECONSTRUCTION"}
    return review_provider_evidence(QUESTION_REGISTRY, records, mapping)


def test_registry_matches_approved_41_id_inventory():
    assert len(QUESTION_REGISTRY) == 41
    assert Counter(q.priority for q in QUESTION_REGISTRY.values()) == {"P0": 18, "P1": 20, "P2": 3}


def test_unknown_id_and_duplicate_and_wrong_category_are_rejected():
    with pytest.raises(ValueError, match="unknown question_id"):
        review([evidence("FAKE-01")])
    with pytest.raises(ValueError, match="duplicate answer"):
        review([evidence("PIT-01"), evidence("PIT-01")])
    wrong = evidence("PIT-01")
    with pytest.raises(ValueError, match="wrong category"):
        review([ProviderEvidenceRecord(**{**wrong.__dict__, "category": "Option quotes"})])


def test_missing_p0_prevents_partial_response_looking_complete():
    result = review([evidence("PIT-01", fields=("trade_price",))])
    assert result.overall_review_status is OverallReviewStatus.INCOMPLETE
    assert result.coverage.total_questions == 41
    assert result.coverage.answered == 1 and result.coverage.P0_missing == 17
    assert result.blocked_changes and not result.proposed_changes


def test_exact_pit_can_only_create_human_review_proposal_and_never_apply_mapping():
    mapping = {"bid": "BLOCKED_UNRESOLVED"}
    item = evidence("PIT-02", fields=("bid",))
    result = review_provider_evidence(QUESTION_REGISTRY, complete_records({"PIT-02": item}), mapping)
    assert result.proposed_changes[0].proposed_mapping_after is ProposalStatus.READY
    assert result.proposed_changes[0].requires_human_review is True
    assert mapping == {"bid": "BLOCKED_UNRESOLVED"}
    assert result.overall_review_status is OverallReviewStatus.READY_FOR_HUMAN_REVIEW
    assert human_review_gate(result) is True


@pytest.mark.parametrize(("text", "correction"), [
    ("Synthetic latest-revised response.", "LATEST_REVISED"),
    ("Synthetic correction behavior unknown.", "UNKNOWN"),
])
def test_latest_revised_or_unknown_corrections_remain_blocked(text, correction):
    item = evidence("PIT-01", text=text, fields=("trade_price",), correction=correction)
    assert review(complete_records({"PIT-01": item})).blocked_changes


def test_critical_ambiguity_is_detected_and_blocks():
    item = evidence("PIT-02", text="Quotes are usually available around that time.", fields=("bid",))
    result = review(complete_records({"PIT-02": item}))
    assert result.ambiguous == ("PIT-02",)
    assert result.blocked_changes
    assert ambiguity_terms(item.raw_response.decode()) == ("usually", "around")


def test_oi_approximate_timing_and_incomplete_dimensions_remain_blocked():
    item = evidence("OI-03", text="OI is normally available around 6:30.",
                    fields=("open_interest",), dimensions=("available_time",))
    result = review(complete_records({"OI-03": item}))
    assert result.blocked_changes and result.ambiguous == ("OI-03",)


def test_oi_fully_evidenced_synthetic_case_is_only_proposed():
    item = evidence("OI-03", fields=("open_interest",), dimensions=tuple(OI_REQUIRED),
                    proposal=ProposalStatus.READY_WITH_CONSERVATIVE_RULE)
    result = review(complete_records({"OI-03": item}))
    assert result.proposed_changes[0].proposed_mapping_after is ProposalStatus.READY_WITH_CONSERVATIVE_RULE


def test_trade_missing_corrections_blocks_but_full_quote_evidence_can_be_proposed():
    trade = evidence("TRD-01", fields=("trade_price",),
                     dimensions=tuple(STREAM_REQUIRED - {"corrections"}), correction="UNKNOWN")
    quote = evidence("QTE-01", fields=("bid",), dimensions=tuple(STREAM_REQUIRED))
    result = review(complete_records({"TRD-01": trade, "QTE-01": quote}))
    assert {p.field for p in result.blocked_changes} == {"trade_price"}
    assert {p.field for p in result.proposed_changes} == {"bid"}


def test_provider_greek_without_pit_blocks_but_complete_local_reconstruction_is_proposed():
    provider = evidence("GRK-02", fields=("gamma",), dimensions=("model_version",))
    local = evidence("GRK-04", fields=("gamma",), dimensions=tuple(GREEK_RECONSTRUCTION_REQUIRED),
                     proposal=ProposalStatus.NEEDS_RECONSTRUCTION)
    blocked = review(complete_records({"GRK-02": provider}))
    reconstruct = review(complete_records({"GRK-04": local}))
    assert blocked.blocked_changes
    assert reconstruct.proposed_changes[0].proposed_mapping_after is ProposalStatus.NEEDS_RECONSTRUCTION


def test_structured_conflicts_are_not_resolved_automatically():
    first = evidence("PIT-01", claims=(("trade.pit", "preserved"),))
    second = evidence("TRD-05", claims=(("trade.pit", "updated_after_corrections"),))
    result = review(complete_records({"PIT-01": first, "TRD-05": second}))
    assert result.contradictory == ("PIT-01", "TRD-05")
    assert result.overall_review_status is OverallReviewStatus.BLOCKED


def test_one_paragraph_can_be_preserved_for_multiple_question_scoped_records():
    paragraph = "One synthetic paragraph, retained unchanged."
    a = evidence("TIM-01", text=paragraph, fragment="shared")
    b = evidence("TIM-02", text=paragraph, fragment="shared")
    result = review([a, b])
    assert result.answered_questions == ("TIM-01", "TIM-02")
    assert a.raw_response == b.raw_response and a.source_fragments == b.source_fragments


def test_raw_bytes_summary_and_interpretation_are_separate_and_immutable():
    item = evidence("PIT-01", text="raw\r\nbytes")
    assert item.raw_response == b"raw\r\nbytes"
    assert item.verbatim_summary != item.interpretation
    with pytest.raises(Exception):
        item.raw_response = b"changed"


def test_confidence_requires_substance_not_provider_authorship():
    assert assess_confidence(exact_answer=True, documentation=True, timestamp_defined=True,
                             corrections_defined=True, point_in_time_defined=True,
                             text="Exact synthetic answer") is Confidence.HIGH
    assert assess_confidence(exact_answer=True, documentation=True, timestamp_defined=True,
                             corrections_defined=True, point_in_time_defined=True,
                             text="Usually exact") is Confidence.LOW


def test_deterministic_ledger_and_fixture_manifest():
    records = [evidence("TIM-02"), evidence("TIM-01")]
    result = review(records)
    assert deterministic_ledger(result, records) == deterministic_ledger(result, reversed(records))
    ledger = json.loads(deterministic_ledger(result, records))
    assert [row["question_id"] for row in ledger] == ["TIM-01", "TIM-02"]
    fixture = json.loads(Path("tests/fixtures/phase5c4b2a_synthetic_responses.json").read_text())
    assert "SYNTHETIC ONLY" in fixture["notice"] and len(fixture["cases"]) == 15

    ambiguous = evidence("PIT-02", text="Usually available.")
    ambiguous_ledger = json.loads(deterministic_ledger(review([ambiguous]), [ambiguous]))
    assert ambiguous_ledger[0]["evidence_class"] == "AMBIGUOUS"


def test_machine_template_is_empty_pending_and_fail_closed():
    template = json.loads(Path("docs/phase5c4b2a_response_template.json").read_text())
    row = template["responses"][0]
    assert row["raw_response"] == ""
    assert row["review_status"] == "PENDING_HUMAN_REVIEW"
    assert row["proposed_mapping_after"] == "BLOCKED_UNRESOLVED"
