from dataclasses import replace
from pathlib import Path

import bot_spx.account_entitlement as contract
from bot_spx.account_entitlement import (
    Capability,
    CapabilityState,
    CausalStatus,
    MappingStatus,
    ProbeOutcome,
    Readiness,
    VerificationEvidence,
    account_state_from_probe,
    capability_contract,
    evaluate_acquisition_readiness,
)


ROOT = Path(__file__).resolve().parents[1]


def test_provider_capability_is_not_account_entitlement():
    for item in contract.CAPABILITY_INVENTORY:
        assert item.provider_capability is CapabilityState.PROVIDER_DOCUMENTED
        assert item.account_entitlement is CapabilityState.ACCOUNT_UNVERIFIED


def test_reported_standard_is_not_verified_standard():
    assert contract.CLAIMED_OR_PREVIOUSLY_REPORTED_PLAN == "STANDARD"
    assert all(i.account_entitlement is not CapabilityState.ACCOUNT_VERIFIED for i in contract.CAPABILITY_INVENTORY)


def test_options_entitlement_never_inherits_to_indices():
    option = replace(capability_contract(Capability.OPTION_QUOTES), account_entitlement=CapabilityState.ACCOUNT_VERIFIED)
    spx = capability_contract(Capability.SPX_INDEX_HISTORY)
    assert option.account_entitlement is CapabilityState.ACCOUNT_VERIFIED
    assert spx.account_entitlement is CapabilityState.ACCOUNT_UNVERIFIED
    assert "separate Indices" in spx.expected_endpoint_family


def test_gamma_not_required_and_provider_greeks_stay_excluded():
    gamma = capability_contract(Capability.OPTION_SECOND_ORDER_GREEKS)
    assert gamma.causal_status is CausalStatus.NOT_REQUIRED_FOR_LOCAL_RECONSTRUCTION
    for cap in (Capability.OPTION_IV, Capability.OPTION_FIRST_ORDER_GREEKS, Capability.OPTION_SECOND_ORDER_GREEKS, Capability.OPTION_EOD_GREEKS):
        assert capability_contract(cap).mapping_status is MappingStatus.EXCLUDED


def test_local_greeks_stay_reconstruction_only():
    assert capability_contract(Capability.OPTION_IV).causal_status is CausalStatus.NEEDS_RECONSTRUCTION
    assert capability_contract(Capability.OPTION_FIRST_ORDER_GREEKS).causal_status is CausalStatus.NEEDS_RECONSTRUCTION


def test_entitlement_does_not_unblock_causal_mappings():
    for cap in (Capability.OPTION_OPEN_INTEREST, Capability.OPTION_QUOTES, Capability.SPX_INDEX_HISTORY):
        item = replace(capability_contract(cap), account_entitlement=CapabilityState.ACCOUNT_VERIFIED)
        assert item.causal_status is CausalStatus.BLOCKED_UNRESOLVED
        assert item.mapping_status is MappingStatus.BLOCKED_UNRESOLVED


def test_history_account_date_remains_unknown():
    assert all(i.account_verified_earliest_accessible_date == contract.UNKNOWN_DATE for i in contract.CAPABILITY_INVENTORY)


def test_readiness_requires_each_independent_evidence_gate():
    item = capability_contract(Capability.OPTION_QUOTES)
    assert evaluate_acquisition_readiness(item, VerificationEvidence()) is Readiness.NEEDS_ACCOUNT_VERIFICATION
    evidence = VerificationEvidence(account_state=CapabilityState.ACCOUNT_VERIFIED)
    assert evaluate_acquisition_readiness(item, evidence) is Readiness.NEEDS_SCHEMA_VERIFICATION
    evidence = replace(evidence, schema_verified=True)
    assert evaluate_acquisition_readiness(item, evidence) is Readiness.NEEDS_RESOLUTION_VERIFICATION
    evidence = replace(evidence, resolution_verified=True)
    assert evaluate_acquisition_readiness(item, evidence) is Readiness.NEEDS_HISTORY_DEPTH_VERIFICATION
    evidence = replace(evidence, history_depth_verified=True)
    assert evaluate_acquisition_readiness(item, evidence) is Readiness.READY_FOR_CONTROLLED_ACQUISITION
    assert item.causal_status is CausalStatus.BLOCKED_UNRESOLVED


def test_denial_blocks_and_excluded_mapping_stays_excluded():
    quote = capability_contract(Capability.OPTION_QUOTES)
    assert evaluate_acquisition_readiness(quote, VerificationEvidence(account_state=CapabilityState.ACCOUNT_DENIED)) is Readiness.BLOCKED
    greek = capability_contract(Capability.OPTION_IV)
    assert evaluate_acquisition_readiness(greek, VerificationEvidence(account_state=CapabilityState.ACCOUNT_VERIFIED)) is Readiness.EXCLUDED


def test_error_empty_and_unproved_denial_are_not_denial():
    assert account_state_from_probe(ProbeOutcome.ERROR) is CapabilityState.ACCOUNT_UNVERIFIED
    assert account_state_from_probe(ProbeOutcome.VERIFIED_AVAILABLE, empty_response=True) is CapabilityState.ACCOUNT_UNVERIFIED
    assert account_state_from_probe(ProbeOutcome.VERIFIED_DENIED) is CapabilityState.ACCOUNT_UNVERIFIED
    assert account_state_from_probe(ProbeOutcome.VERIFIED_DENIED, explicit_entitlement_denial=True) is CapabilityState.ACCOUNT_DENIED


def test_probe_plan_is_minimal_read_only_and_non_persistent():
    assert tuple(a.order for a in contract.ACCOUNT_VERIFICATION_PLAN) == tuple(range(1, 11))
    for action in contract.ACCOUNT_VERIFICATION_PLAN:
        assert action.maximum_rows_permitted <= 10000
        assert "one" in action.minimum_requested_scope
        assert "one trading day only" in action.date_range
        assert action.raw_payload_may_be_persisted is False


def test_offline_safety_and_authorization_gate():
    assert contract.CREDENTIAL_READS == 0
    assert contract.AUTHENTICATED_CALLS == 0
    assert contract.PROVIDER_DATA_CALLS == 0
    assert contract.DATASETS_DOWNLOADED == 0
    assert contract.CONTROLLED_ACCOUNT_VERIFICATION_AUTHORIZED is False
    assert contract.can_execute_verification_plan() is False
    assert contract.CUTOVER == "NO"


def test_module_has_no_network_or_credential_capability():
    source = (ROOT / "src/bot_spx/account_entitlement.py").read_text()
    forbidden = ("import requests", "import urllib", "import socket", "import subprocess", "dotenv", "getenv", "environ[")
    assert all(token not in source for token in forbidden)


def test_runtime_and_protected_modules_do_not_import_contract():
    for relative in ("spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py", "spx_data_FASE5.py", "src/bot_spx/historical.py", "src/bot_spx/historical_provider_spec.py", "src/bot_spx/local_greeks.py", "src/bot_spx/causal_greeks_inputs.py"):
        source = (ROOT / relative).read_text()
        assert "import bot_spx.account_entitlement" not in source
        assert "from bot_spx.account_entitlement" not in source


def test_inventory_and_evaluation_are_deterministic():
    assert len(contract.CAPABILITY_INVENTORY) == len(Capability) == 12
    evidence = VerificationEvidence(account_state=CapabilityState.ACCOUNT_VERIFIED, schema_verified=True, resolution_verified=True, history_depth_verified=True)
    first = tuple(evaluate_acquisition_readiness(i, evidence) for i in contract.CAPABILITY_INVENTORY)
    second = tuple(evaluate_acquisition_readiness(i, evidence) for i in contract.CAPABILITY_INVENTORY)
    assert first == second
