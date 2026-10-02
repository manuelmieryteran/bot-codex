import json
from pathlib import Path

import pytest

from bot_spx.replay_readiness import (
    COMPONENTS,
    CUTOVER,
    DEPENDENCIES,
    DEPTH_MATRIX,
    FEATURE_REQUIREMENTS,
    MAPPING_PROMOTIONS,
    MINIMUM_PROVENANCE_FIELDS,
    PROMOTION_GATES,
    TRADE_REQUIREMENTS,
    DataRequirement,
    Dependency,
    ReadinessState,
    SessionStatus,
    contract_dict,
    evaluate_session_replay_readiness,
    validate_dag,
)

ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "docs/evidence/phase5c4b5a_replay_readiness.json"
ACCOUNT = ROOT / "docs/evidence/phase5c4b4c2_thetadata_account/evidence_summary.json"


def test_machine_readable_artifact_is_exactly_generated_contract():
    assert json.loads(ARTIFACT.read_text()) == contract_dict()
    assert MAPPING_PROMOTIONS == 0
    assert CUTOVER == "NO"


def test_closed_taxonomy_and_all_mandatory_components_are_present():
    expected = {
        "historical_spxw_0dte_universe", "option_quotes", "option_trades",
        "open_interest", "spx_historical_spot", "interest_rate",
        "dividend_policy", "contract_metadata", "local_iv_reconstruction",
        "local_greeks_reconstruction", "cross_feed_temporal_alignment",
        "corrections_cancels_policy", "missingness_policy", "staleness_policy",
        "session_calendar_expiration", "historical_depth",
        "deterministic_provenance", "replay_bundle_eligibility",
        "loader_readiness", "backtest_readiness",
    }
    assert {item.component for item in COMPONENTS} == expected
    assert all(isinstance(item.state, ReadinessState) for item in COMPONENTS)


def test_frozen_account_evidence_has_exactly_seven_available_and_anomalies():
    evidence = json.loads(ACCOUNT.read_text())
    assert evidence["outcome_counts"]["VERIFIED_AVAILABLE"] == 7
    assert len(evidence["acquisition_capabilities"]) == 7
    probes = {item["probe_id"]: item for item in evidence["per_probe_summary"]}
    assert (probes["P4"]["outcome"], probes["P4"]["status_class"]) == ("AMBIGUOUS", "EMPTY_SUCCESS")
    assert (probes["P8"]["outcome"], probes["P8"]["status_class"]) == ("ERROR", "TRANSPORT_ERROR")
    assert probes["P2"]["row_count"] == 17_326
    assert evidence["scope_anomalies"][0]["classification"] == "ACQUISITION_SCOPE_ANOMALY"
    assert set(evidence["historical_depth_status"].values()) == {"SINGLE_DATE_ONLY"}
    assert evidence["account_metadata_interpretation"]["ACCOUNT_TIER_VALUE"] == "NOT_PERSISTED"


def test_dependency_graph_is_acyclic_and_contains_every_edge_endpoint():
    order = validate_dag()
    position = {node: index for index, node in enumerate(order)}
    assert all(position[e.prerequisite] < position[e.dependent] for e in DEPENDENCIES)
    with pytest.raises(ValueError, match="cycle"):
        validate_dag((Dependency("a", "b"), Dependency("b", "a")))


def test_every_promotion_is_manual_and_has_objective_gate_fields():
    assert PROMOTION_GATES
    for gate in PROMOTION_GATES:
        assert gate.automatic_promotion_allowed is False
        assert gate.required_evidence
        assert gate.required_implementation
        assert gate.required_tests
        assert gate.promotion_target


def test_session_gate_fails_closed_and_accumulates_all_blockers():
    states = {
        "universe": ReadinessState.RESOLVED_WITH_CONSERVATIVE_RULE,
        "quote": ReadinessState.BLOCKED_AVAILABILITY,
        "spx": ReadinessState.BLOCKED_ACQUISITION,
    }
    result = evaluate_session_replay_readiness(("universe", "quote", "spx"), states)
    assert result.status is SessionStatus.BLOCKED
    assert result.blockers == (
        "quote:BLOCKED_AVAILABILITY", "spx:BLOCKED_ACQUISITION"
    )
    assert evaluate_session_replay_readiness((), states).status is SessionStatus.INVALID
    assert evaluate_session_replay_readiness(("unknown",), states).status is SessionStatus.INVALID
    assert evaluate_session_replay_readiness(("universe",), states).status is SessionStatus.READY


def test_acquisition_state_cannot_be_passed_as_causal_readiness():
    with pytest.raises(AttributeError):
        evaluate_session_replay_readiness(("quote",), {"quote": "VERIFIED_AVAILABLE"})


def test_trade_requirements_keep_acquisition_and_feature_need_separate():
    assert TRADE_REQUIREMENTS == {
        "quote_based_iv_reconstruction": DataRequirement.NOT_REQUIRED,
        "dealer_flow_estimation": DataRequirement.REQUIRED,
        "aggressor_classification": DataRequirement.REQUIRED,
        "dynamic_gex": DataRequirement.REQUIRED,
        "signal_reconstruction": DataRequirement.OPTIONAL,
    }


def test_feature_matrix_is_complete_and_blocked():
    expected = {
        "SPX spot", "Call Wall", "Put Wall", "Gamma Flip / Zero Gamma",
        "Static OI/GEX", "Dynamic GEX", "Dealer flow", "Dealer Dynamic GEX",
        "Gamma Balance", "Gamma Regime", "Mean Reversion signal",
        "Breakout/Breakdown signal", "Risk gate", "Entry permission",
    }
    assert {item.feature for item in FEATURE_REQUIREMENTS} == expected
    assert not any(item.current_readiness is ReadinessState.RESOLVED for item in FEATURE_REQUIREMENTS)


def test_depth_and_provenance_remain_fail_closed():
    assert DEPTH_MATRIX
    assert all(item.account_verified_depth == "2026-01-15/SINGLE_DATE_ONLY" for item in DEPTH_MATRIX)
    assert all(item.required_backtest_depth == "HUMAN_DECISION_PENDING" for item in DEPTH_MATRIX)
    assert all(item.state is ReadinessState.BLOCKED_HISTORICAL_DEPTH for item in DEPTH_MATRIX)
    assert set(MINIMUM_PROVENANCE_FIELDS) == {
        "provider", "dataset", "contract_identity", "event_time", "available_time",
        "source_or_reference_time", "retrieval_context", "policy_version",
        "mapping_version", "model_version", "transformation_version",
    }


def test_phase_is_offline_and_does_not_add_operational_imports():
    source = (ROOT / "src/bot_spx/replay_readiness.py").read_text()
    forbidden = ("requests", "httpx", "thetadata", "tradestation", "subprocess", "socket")
    assert all(f"import {name}" not in source for name in forbidden)
