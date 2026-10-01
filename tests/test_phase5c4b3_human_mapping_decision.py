import hashlib
from pathlib import Path

from bot_spx.historical_provider_spec import (
    DecisionStatus,
    EVIDENCE_LEDGER,
    HUMAN_MAPPING_DECISIONS,
    Confidence,
)


ROOT = Path(__file__).resolve().parents[1]
DECISIONS = {item.subject: item for item in HUMAN_MAPPING_DECISIONS}


def test_exact_human_approved_decision_set_and_evidence_reference():
    assert set(DECISIONS) == {
        "open_interest", "option_trades", "option_quotes",
        "spx_historical_spot", "provider_historical_greeks_iv",
        "locally_reconstructed_greeks_iv", "historical_spxw_0dte_universe",
        "provider_capability", "our_account_entitlement",
    }
    assert all(row.evidence_reference == EVIDENCE_LEDGER for row in DECISIONS.values())
    assert all(row.human_decision_status == "HUMAN_APPROVED" for row in DECISIONS.values())
    assert all("5C-4B.3" in row.human_decision_reference for row in DECISIONS.values())


def test_critical_feeds_remain_blocked_with_negative_promotion_guards():
    for subject in ("open_interest", "option_trades", "option_quotes", "spx_historical_spot"):
        assert DECISIONS[subject].status is DecisionStatus.BLOCKED_UNRESOLVED
        assert DECISIONS[subject].status not in {
            DecisionStatus.READY, DecisionStatus.READY_WITH_CONSERVATIVE_RULE,
        }


def test_greeks_decisions_are_strictly_separated():
    provider = DECISIONS["provider_historical_greeks_iv"]
    local = DECISIONS["locally_reconstructed_greeks_iv"]
    assert provider.status is DecisionStatus.EXCLUDED
    assert local.status is DecisionStatus.NEEDS_RECONSTRUCTION
    assert "not to otherwise eligible inputs" in provider.residual_risk
    for requirement in ("option price/quote", "underlying", "rate", "SOFR", "input timestamps"):
        assert requirement in local.temporal_semantics
    for requirement in ("Dividend", "expiration", "model version", "deterministic"):
        assert requirement in local.correction_semantics


def test_spxw_universe_is_only_low_confidence_conservative_rule():
    universe = DECISIONS["historical_spxw_0dte_universe"]
    assert universe.status is DecisionStatus.READY_WITH_CONSERVATIVE_RULE
    assert universe.confidence is Confidence.LOW
    assert all(term in universe.temporal_semantics for term in ("root=SPXW", "expiration=D", "trade/quote"))
    assert all(term in universe.residual_risk for term in ("inactive", "metadata", "holiday"))


def test_provider_capability_never_implies_account_entitlement():
    capability = DECISIONS["provider_capability"]
    entitlement = DECISIONS["our_account_entitlement"]
    assert capability.status is DecisionStatus.READY
    assert entitlement.status is DecisionStatus.BLOCKED_UNRESOLVED
    assert capability.subject != entitlement.subject
    assert "not inferred" in entitlement.temporal_semantics


def test_no_latency_bound_and_event_time_is_not_available_time():
    assert all(row.latency_bound is None for row in DECISIONS.values())
    assert "event_time is not proven available_time" in DECISIONS["open_interest"].temporal_semantics
    for subject in ("option_trades", "option_quotes", "spx_historical_spot"):
        semantics = DECISIONS[subject].temporal_semantics
        assert "receipt time" in semantics or "availability bound" in semantics


def test_no_automatic_additional_promotions():
    promoted = {
        row.subject for row in HUMAN_MAPPING_DECISIONS
        if row.status in {DecisionStatus.READY, DecisionStatus.READY_WITH_CONSERVATIVE_RULE}
    }
    assert promoted == {"provider_capability", "historical_spxw_0dte_universe"}


def test_phase5c4b2_evidence_is_byte_for_byte_unchanged():
    expected = {
        "raw_response.md": "12d56f13a04f94deb6c74dc53fe16d8f888f4a3ecc2a2fdda81c74d49157728d",
        "evidence_ledger.json": "ac1365e2848a3f9e587e0795b5d887e8c9829bb7fe81e5038d876418aac8c069",
    }
    evidence_dir = ROOT / "docs/evidence/phase5c4b2_thetadata"
    for filename, digest in expected.items():
        assert hashlib.sha256((evidence_dir / filename).read_bytes()).hexdigest() == digest


def test_protected_runtime_is_unchanged_and_decision_has_no_cutover():
    assert hashlib.sha256((ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py").read_bytes()).hexdigest() == (
        "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023"
    )
    record = (ROOT / "docs/evidence/phase5c4b3_human_mapping_decision.md").read_text()
    assert "cutover=NO" in record
    assert "no data ingestion" in record
    assert "no backtest" in record
