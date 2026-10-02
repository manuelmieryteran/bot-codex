import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from bot_spx.causal_policy_docket import (
    CURRENT_BLOCKER_COUNT, CUTOVER, DECISION_PACKETS, DOCKETS, DOCKET_BY_ID,
    EVIDENCE_REQUESTS, FROZEN_INPUTS, LOCAL_GREEKS_DEPENDENCY_CHAIN,
    MAPPING_PROMOTIONS, MINIMIZATION_PRINCIPLE, NEXT_ACTIONS, RESOLUTION_EDGES,
    TRADE_FEATURE_DERIVATION, BlockerDocket, DecisionPacketStatus,
    DecisionRequirement, DocketStatus, EvidenceStatus, ResolutionEdge,
    contract_dict, validate_resolution_dag,
)

ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "docs/evidence/phase5c4b5b_causal_policy_docket.json"


def test_artifact_is_exact_generated_contract_and_frozen_state_is_unchanged():
    assert json.loads(ARTIFACT.read_text()) == contract_dict()
    assert CURRENT_BLOCKER_COUNT == len(DOCKETS) == 19
    assert MAPPING_PROMOTIONS == 0 and CUTOVER == "NO"
    assert FROZEN_INPUTS["available_capabilities"] == 7
    assert FROZEN_INPUTS["P2_row_count"] == 17326
    assert FROZEN_INPUTS["historical_depth"] == "SINGLE_DATE_ONLY"


def test_exactly_b01_through_b19_are_separate_immutable_dockets():
    assert tuple(item.blocker_id for item in DOCKETS) == tuple(f"B{i:02d}" for i in range(1, 20))
    assert set(DOCKET_BY_ID) == {f"B{i:02d}" for i in range(1, 20)}
    assert all(isinstance(item.status, DocketStatus) for item in DOCKETS)
    assert all(isinstance(item.evidence_status, EvidenceStatus) for item in DOCKETS)
    assert all(isinstance(item.human_decision_required, DecisionRequirement) for item in DOCKETS)
    assert all(item.automatic_promotion_allowed is False for item in DOCKETS)
    with pytest.raises(FrozenInstanceError):
        DOCKETS[0].name = "changed"
    with pytest.raises(TypeError):
        DOCKET_BY_ID["B01"] = DOCKETS[0]


def test_every_docket_has_objective_future_gate_and_fail_closed_content():
    for docket in DOCKETS:
        assert docket.persisted_evidence_refs and docket.persisted_evidence_summary
        assert docket.decision_question and docket.admissible_decision_classes
        assert docket.prohibited_decision_classes and docket.lookahead_risk
        assert docket.residual_risks and docket.required_future_implementation
        assert docket.required_future_tests and docket.promotion_target
        assert docket.promotion_preconditions


def test_decision_packets_are_pending_and_cover_every_blocker_without_merging_them():
    assert tuple(packet.decision_id for packet in DECISION_PACKETS) == tuple(f"Q{i}" for i in range(1, 10))
    assert all(packet.status is DecisionPacketStatus.PENDING for packet in DECISION_PACKETS)
    assert {b for packet in DECISION_PACKETS for b in packet.related_blockers} == set(DOCKET_BY_ID)
    assert all(packet.requires_future_authorization for packet in DECISION_PACKETS)


def test_evidence_plan_is_minimal_authorized_and_never_executed():
    assert EVIDENCE_REQUESTS
    assert all(item.human_authorization_required for item in EVIDENCE_REQUESTS)
    assert all(item.minimum_scope and item.stop_conditions for item in EVIDENCE_REQUESTS)
    assert MINIMIZATION_PRINCIPLE["bulk"] is False
    assert MINIMIZATION_PRINCIPLE["crawler"] is False
    assert "17326" in MINIMIZATION_PRINCIPLE["reason"]
    assert contract_dict()["phase_actions_executed"] == []
    assert contract_dict()["policies_approved"] == []


def test_resolution_dag_is_deterministic_acyclic_and_only_uses_known_ids():
    order = validate_resolution_dag()
    assert order == validate_resolution_dag(tuple(reversed(RESOLUTION_EDGES)))
    assert set(order) == set(DOCKET_BY_ID)
    positions = {node: i for i, node in enumerate(order)}
    assert all(positions[e.prerequisite] < positions[e.dependent] for e in RESOLUTION_EDGES)
    with pytest.raises(ValueError, match="unknown blocker"):
        validate_resolution_dag((ResolutionEdge("B01", "B20"),))
    with pytest.raises(ValueError, match="cycle"):
        validate_resolution_dag((ResolutionEdge("B01", "B02"), ResolutionEdge("B02", "B01")))


def test_temporal_prohibitions_and_missingness_are_explicit():
    assert "EVENT_TIME_EQUALS_AVAILABLE_TIME_WITHOUT_EVIDENCE" in DOCKET_BY_ID["B01"].prohibited_decision_classes
    assert "NO_ROW_EQUALS_ZERO" in DOCKET_BY_ID["B06"].prohibited_decision_classes
    assert {"NEAREST_FUTURE", "FUTURE_INTERPOLATION", "FUTURE_BACKFILL"} <= set(DOCKET_BY_ID["B11"].prohibited_decision_classes)
    assert "SILENT_FORWARD_FILL" in DOCKET_BY_ID["B10"].prohibited_decision_classes


def test_trade_derivation_and_greeks_chain_do_not_create_eligibility_or_mode():
    assert "Dealer flow" in TRADE_FEATURE_DERIVATION["trades_required"]
    assert "quote-based local IV" in TRADE_FEATURE_DERIVATION["without_trades"]
    assert TRADE_FEATURE_DERIVATION["operational_degraded_mode_created"] is False
    assert LOCAL_GREEKS_DEPENDENCY_CHAIN["currently_eligible_inputs"] == ()
    assert LOCAL_GREEKS_DEPENDENCY_CHAIN["provider_greeks_iv"] == "EXCLUDED"


def test_next_actions_are_declarative_and_dependency_ordered():
    assert all(action.execute_in_this_phase is False for action in NEXT_ACTIONS)
    positions = {item.action_id: index for index, item in enumerate(NEXT_ACTIONS)}
    assert all(positions[p] < positions[item.action_id] for item in NEXT_ACTIONS for p in item.prerequisite_actions)


def test_module_has_no_operational_imports_or_provider_calls():
    source = (ROOT / "src/bot_spx/causal_policy_docket.py").read_text()
    forbidden = ("import requests", "import httpx", "import socket", "import subprocess")
    assert all(token not in source.lower() for token in forbidden)
