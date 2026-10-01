import hashlib
import json
from pathlib import Path

from bot_spx.provider_evidence_review import QUESTION_REGISTRY


ROOT = Path(__file__).parents[1]
EVIDENCE = ROOT / "docs/evidence/phase5c4b2_thetadata"
RAW = EVIDENCE / "raw_response.md"
LEDGER = EVIDENCE / "evidence_ledger.json"


def ledger():
    return json.loads(LEDGER.read_text())


def reviews():
    return {row["question_id"]: row for row in ledger()["question_reviews"]}


def proposals():
    return {row["field"]: row for row in ledger()["proposed_mapping_changes"]}


def test_raw_response_is_preserved_with_registered_hash_and_unknown_timestamp():
    data = ledger()
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == data["raw_response"]["sha256"]
    assert data["received_at"] == "UNKNOWN" and data["support_reference"] == "UNKNOWN"
    assert data["support_author"] == "Eduardo" and data["support_channel"] == "support ticket"


def test_real_response_covers_exact_registry_with_real_partial_and_missing_counts():
    data = ledger()
    assert set(reviews()) == set(QUESTION_REGISTRY)
    assert data["coverage"] == {
        "registry": 41, "answered": 23, "partially_answered": 18, "unanswered": 0,
        "P0": {"answered": 13, "partial": 5, "missing": 0},
        "P1": {"answered": 8, "partial": 12, "missing": 0},
        "P2": {"answered": 2, "partial": 1, "missing": 0},
    }


def test_every_question_remains_pending_human_review():
    data = ledger()
    assert data["human_review_required"] is True
    assert data["automatic_approvals"] == 0
    assert {row["review_status"] for row in data["question_reviews"]} == {"PENDING_HUMAN_REVIEW"}
    assert all(row["requires_human_review"] for row in data["proposed_mapping_changes"])


def test_oi_event_timestamp_is_not_guaranteed_client_availability():
    assert "not client availability" in reviews()["OI-03"]["support_statement"]
    assert "No causal rule" in proposals()["open_interest"]["available_time_rule"]
    assert proposals()["open_interest"]["status"] == "BLOCKED_UNRESOLVED"


def test_average_under_three_ms_is_not_a_latency_bound():
    statement = reviews()["TIM-02"]["support_statement"]
    assert "not a maximum" in statement
    assert any(item["term"] == "average / averaging" for item in ledger()["ambiguities"])


def test_oi_missing_row_is_not_zero():
    assert "absence is not zero" in reviews()["OI-05"]["support_statement"]


def test_oi_zero_row_is_a_reported_zero():
    assert "explicit zero is OPRA-reported zero" in reviews()["OI-05"]["support_statement"]


def test_multiple_oi_rows_preserve_chronology_without_invented_correction_identity():
    rule = proposals()["open_interest"]["correction_rule"]
    assert "Preserve every row chronologically" in rule
    assert "correction identity is unknown" in rule


def test_trade_sequence_is_not_globally_unique_and_has_no_dedup_contract():
    statement = reviews()["TRD-02"]["support_statement"]
    residual = proposals()["trade_tape"]["residual_ambiguity"]
    assert "not globally unique" in statement
    assert "dedup key" in residual


def test_trade_cancel_has_no_original_link_field():
    assert "no link to its original" in reviews()["TRD-03"]["support_statement"]


def test_quote_has_no_sequence_and_remains_blocked():
    assert "no sequence" in reviews()["QTE-02"]["support_statement"]
    assert proposals()["quote_tape"]["status"] == "BLOCKED_UNRESOLVED"


def test_provider_greeks_are_compute_on_request_and_not_pit_outputs():
    assert "recomputed on request" in reviews()["GRK-02"]["support_statement"]
    assert proposals()["provider_historical_greeks_iv"]["status"] == "EXCLUDED"


def test_historical_same_date_sofr_is_noncausal_intraday_by_default():
    rule = proposals()["local_greeks_iv"]["available_time_rule"]
    assert "never use same-date retrospective SOFR intraday by default" in rule


def test_local_reconstruction_is_separate_and_not_ready():
    local = proposals()["local_greeks_iv"]
    provider = proposals()["provider_historical_greeks_iv"]
    assert local["status"] == "NEEDS_RECONSTRUCTION"
    assert provider["status"] == "EXCLUDED"
    assert local["field"] != provider["field"]


def test_no_mapping_or_runtime_activity_and_no_cutover():
    safety = ledger()["safety"]
    assert safety["mapping_modifications"] == safety["runtime_modifications"] == 0
    assert safety["automatic_approvals"] == 0 and safety["cutover"] == "NO"


def test_documentation_failure_does_not_erase_provider_confirmation():
    data = ledger()
    assert len(data["documentation_checks"]) == 13
    assert {row["result"] for row in data["documentation_checks"]} == {"UNVERIFIED_ENVIRONMENT"}
    assert data["classifications"] == {"PROVIDER_WRITTEN_CONFIRMATION": 35, "AMBIGUOUS": 6}


def test_no_false_contradictions_and_shared_fragments_are_independently_reviewed():
    data = ledger()
    assert data["contradictions"] == []
    assert reviews()["TIM-01"]["source_fragment_id"] == reviews()["TRD-01"]["source_fragment_id"]
    assert reviews()["TIM-01"]["question_id"] != reviews()["TRD-01"]["question_id"]
