"""Offline account-entitlement and controlled-acquisition contract.

This module deliberately contains only immutable declarations and pure logic.
It does not know how to read credentials, use a provider client, or perform I/O.
Provider documentation, account access, acquisition readiness, and causal replay
are separate gates; passing one never promotes another.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class CapabilityState(str, Enum):
    PROVIDER_DOCUMENTED = "PROVIDER_DOCUMENTED"
    ACCOUNT_VERIFIED = "ACCOUNT_VERIFIED"
    ACCOUNT_UNVERIFIED = "ACCOUNT_UNVERIFIED"
    ACCOUNT_DENIED = "ACCOUNT_DENIED"
    UNKNOWN = "UNKNOWN"
    NOT_REQUIRED = "NOT_REQUIRED"
    EXCLUDED = "EXCLUDED"


class Readiness(str, Enum):
    READY_FOR_CONTROLLED_ACQUISITION = "READY_FOR_CONTROLLED_ACQUISITION"
    NEEDS_ACCOUNT_VERIFICATION = "NEEDS_ACCOUNT_VERIFICATION"
    NEEDS_SCHEMA_VERIFICATION = "NEEDS_SCHEMA_VERIFICATION"
    NEEDS_HISTORY_DEPTH_VERIFICATION = "NEEDS_HISTORY_DEPTH_VERIFICATION"
    NEEDS_RESOLUTION_VERIFICATION = "NEEDS_RESOLUTION_VERIFICATION"
    NEEDS_CAUSALITY_RESOLUTION = "NEEDS_CAUSALITY_RESOLUTION"
    BLOCKED = "BLOCKED"
    EXCLUDED = "EXCLUDED"


class Capability(str, Enum):
    OPTIONS_CONTRACT_LIST = "OPTIONS_CONTRACT_LIST"
    OPTION_QUOTES = "OPTION_QUOTES"
    OPTION_TRADES = "OPTION_TRADES"
    OPTION_OPEN_INTEREST = "OPTION_OPEN_INTEREST"
    OPTION_IV = "OPTION_IV"
    OPTION_FIRST_ORDER_GREEKS = "OPTION_FIRST_ORDER_GREEKS"
    OPTION_SECOND_ORDER_GREEKS = "OPTION_SECOND_ORDER_GREEKS"
    OPTION_EOD_GREEKS = "OPTION_EOD_GREEKS"
    SPX_INDEX_HISTORY = "SPX_INDEX_HISTORY"
    INTEREST_RATE_HISTORY = "INTEREST_RATE_HISTORY"
    CONTRACT_METADATA = "CONTRACT_METADATA"
    TRADE_QUOTE = "TRADE_QUOTE"


class Requirement(str, Enum):
    REQUIRED_NOW = "REQUIRED_NOW"
    REQUIRED_LATER = "REQUIRED_LATER"
    OPTIONAL = "OPTIONAL"
    NOT_REQUIRED = "NOT_REQUIRED"
    EXCLUDED = "EXCLUDED"


class Resolution(str, Enum):
    TICK = "TICK"
    VENUE = "VENUE"
    ONE_MINUTE = "ONE_MINUTE"
    EOD = "EOD"
    UNKNOWN = "UNKNOWN"


class CausalStatus(str, Enum):
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    NEEDS_RECONSTRUCTION = "NEEDS_RECONSTRUCTION"
    NOT_REQUIRED_FOR_LOCAL_RECONSTRUCTION = "NOT_REQUIRED_FOR_LOCAL_RECONSTRUCTION"
    UNKNOWN = "UNKNOWN"


class MappingStatus(str, Enum):
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"
    NEEDS_RECONSTRUCTION = "NEEDS_RECONSTRUCTION"
    EXCLUDED = "EXCLUDED"
    READY_WITH_CONSERVATIVE_RULE = "READY_WITH_CONSERVATIVE_RULE"
    UNKNOWN = "UNKNOWN"


class VerificationActionType(str, Enum):
    READ_ACCOUNT_METADATA = "READ_ACCOUNT_METADATA"
    MINIMAL_SCHEMA_PROBE = "MINIMAL_SCHEMA_PROBE"
    MINIMAL_SINGLE_CONTRACT_PROBE = "MINIMAL_SINGLE_CONTRACT_PROBE"
    MINIMAL_SINGLE_TIMESTAMP_PROBE = "MINIMAL_SINGLE_TIMESTAMP_PROBE"
    MINIMAL_SINGLE_DAY_PROBE = "MINIMAL_SINGLE_DAY_PROBE"


class RetentionClass(str, Enum):
    METADATA_ONLY = "METADATA_ONLY"
    SCHEMA_SAMPLE = "SCHEMA_SAMPLE"
    CONTROLLED_DATA_SAMPLE = "CONTROLLED_DATA_SAMPLE"


class ProbeOutcome(str, Enum):
    VERIFIED_AVAILABLE = "VERIFIED_AVAILABLE"
    VERIFIED_DENIED = "VERIFIED_DENIED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_TESTED = "NOT_TESTED"
    ERROR = "ERROR"


UNKNOWN_DATE = "UNKNOWN"
CLAIMED_OR_PREVIOUSLY_REPORTED_PLAN = "STANDARD"
CONTROLLED_ACCOUNT_VERIFICATION_AUTHORIZED = False
CUTOVER = "NO"

# Phase 5C-4B.4C-1 safety ledger. These constants are declarations verified by
# tests and are not counters around hidden operational code (there is none).
AUTHENTICATED_CALLS = 0
CREDENTIAL_READS = 0
PROVIDER_DATA_CALLS = 0
DATASETS_DOWNLOADED = 0


@dataclass(frozen=True)
class VerificationEvidence:
    account_state: CapabilityState = CapabilityState.ACCOUNT_UNVERIFIED
    schema_verified: bool = False
    resolution_verified: bool = False
    history_depth_verified: bool = False
    probe_outcome: ProbeOutcome = ProbeOutcome.NOT_TESTED
    empty_response: bool = False


@dataclass(frozen=True)
class CapabilityContract:
    capability: Capability
    purpose: str
    requirement: Requirement
    provider_capability: CapabilityState
    account_entitlement: CapabilityState
    required_resolution: Resolution
    required_historical_depth: str
    provider_documented_start_date: str
    account_verified_earliest_accessible_date: str
    required_fields: Tuple[str, ...]
    expected_endpoint_family: str
    causal_status: CausalStatus
    mapping_status: MappingStatus
    acquisition_readiness: Readiness
    evidence_reference: str
    verification_required: bool = True


@dataclass(frozen=True)
class VerificationAction:
    order: int
    action_type: VerificationActionType
    capability: Capability
    endpoint_family: str
    authentication_required: bool
    minimum_requested_scope: str
    maximum_rows_permitted: int
    date_range: str
    symbol_or_root: str
    fields_expected: Tuple[str, ...]
    success_evidence: str
    denial_evidence: str
    ambiguous_outcome: str
    retention: RetentionClass
    raw_payload_may_be_persisted: bool = False


def evaluate_acquisition_readiness(
    capability: CapabilityContract, evidence: VerificationEvidence
) -> Readiness:
    """Evaluate acquisition only; deliberately ignore causal replay status."""
    if capability.requirement is Requirement.EXCLUDED or capability.mapping_status is MappingStatus.EXCLUDED:
        return Readiness.EXCLUDED
    if evidence.account_state is CapabilityState.ACCOUNT_DENIED:
        return Readiness.BLOCKED
    if evidence.account_state is not CapabilityState.ACCOUNT_VERIFIED:
        return Readiness.NEEDS_ACCOUNT_VERIFICATION
    if not evidence.schema_verified:
        return Readiness.NEEDS_SCHEMA_VERIFICATION
    if not evidence.resolution_verified:
        return Readiness.NEEDS_RESOLUTION_VERIFICATION
    if not evidence.history_depth_verified:
        return Readiness.NEEDS_HISTORY_DEPTH_VERIFICATION
    return Readiness.READY_FOR_CONTROLLED_ACQUISITION


def account_state_from_probe(
    outcome: ProbeOutcome, *, explicit_entitlement_denial: bool = False, empty_response: bool = False
) -> CapabilityState:
    """Translate only conclusive evidence; errors and empty results stay unknown."""
    if outcome is ProbeOutcome.VERIFIED_AVAILABLE and not empty_response:
        return CapabilityState.ACCOUNT_VERIFIED
    if outcome is ProbeOutcome.VERIFIED_DENIED and explicit_entitlement_denial:
        return CapabilityState.ACCOUNT_DENIED
    return CapabilityState.ACCOUNT_UNVERIFIED


EVIDENCE = "docs/evidence/phase5c4b2_thetadata/raw_response.md"
CAUSAL_CONTRACT = "docs/phase5c4b4b_causal_input_contract.md"


def _item(
    capability: Capability,
    purpose: str,
    requirement: Requirement,
    resolution: Resolution,
    depth: str,
    provider_start: str,
    fields: Tuple[str, ...],
    family: str,
    causal: CausalStatus = CausalStatus.UNKNOWN,
    mapping: MappingStatus = MappingStatus.UNKNOWN,
) -> CapabilityContract:
    return CapabilityContract(
        capability, purpose, requirement, CapabilityState.PROVIDER_DOCUMENTED,
        CapabilityState.ACCOUNT_UNVERIFIED, resolution, depth, provider_start,
        UNKNOWN_DATE, fields, family, causal, mapping,
        Readiness.NEEDS_ACCOUNT_VERIFICATION, EVIDENCE, True,
    )


CAPABILITY_INVENTORY: Tuple[CapabilityContract, ...] = (
    _item(Capability.OPTIONS_CONTRACT_LIST, "discover the bounded contract universe", Requirement.REQUIRED_NOW, Resolution.UNKNOWN, "project replay range (unresolved)", "UNKNOWN", ("root", "expiration", "strike", "right"), "option contract/list"),
    _item(Capability.OPTION_QUOTES, "local IV/Greeks premium input", Requirement.REQUIRED_NOW, Resolution.TICK, "project replay range (unresolved)", "2016-01-01", ("timestamp", "bid", "ask", "bid_size", "ask_size", "contract_identity", "condition_when_available", "exchange_when_available"), "historical option quote", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.BLOCKED_UNRESOLVED),
    _item(Capability.OPTION_TRADES, "strategy trade tape", Requirement.REQUIRED_LATER, Resolution.TICK, "project replay range (unresolved)", "2016-01-01", ("timestamp", "price", "size", "condition", "sequence_when_applicable", "contract_identity"), "historical option trade", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.BLOCKED_UNRESOLVED),
    _item(Capability.OPTION_OPEN_INTEREST, "strategy state and future local analytics", Requirement.REQUIRED_LATER, Resolution.EOD, "project replay range (unresolved)", "2020-01-01", ("timestamp", "value", "contract_identity"), "historical option open interest", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.BLOCKED_UNRESOLVED),
    _item(Capability.OPTION_IV, "provider diagnostic only; PIT output excluded", Requirement.OPTIONAL, Resolution.TICK, "diagnostic range only", "2016-01-01", ("timestamp", "iv", "contract_identity"), "historical option IV", CausalStatus.NEEDS_RECONSTRUCTION, MappingStatus.EXCLUDED),
    _item(Capability.OPTION_FIRST_ORDER_GREEKS, "provider diagnostic only", Requirement.OPTIONAL, Resolution.TICK, "diagnostic range only", "2017-01-01", ("timestamp", "delta", "theta", "vega", "rho", "contract_identity"), "historical option Greeks", CausalStatus.NEEDS_RECONSTRUCTION, MappingStatus.EXCLUDED),
    _item(Capability.OPTION_SECOND_ORDER_GREEKS, "optional comparison; local reconstruction does not require provider Gamma", Requirement.NOT_REQUIRED, Resolution.TICK, "not required", "2017-01-01", ("timestamp", "gamma", "contract_identity"), "historical option second/third-order Greeks", CausalStatus.NOT_REQUIRED_FOR_LOCAL_RECONSTRUCTION, MappingStatus.EXCLUDED),
    _item(Capability.OPTION_EOD_GREEKS, "optional EOD Gamma diagnostic", Requirement.OPTIONAL, Resolution.EOD, "diagnostic range only", "2017-01-01", ("timestamp", "gamma", "contract_identity"), "historical option EOD Greeks", CausalStatus.NOT_REQUIRED_FOR_LOCAL_RECONSTRUCTION, MappingStatus.EXCLUDED),
    _item(Capability.SPX_INDEX_HISTORY, "underlying input for local IV/Greeks", Requirement.REQUIRED_NOW, Resolution.VENUE, "project replay range (unresolved)", "2017-01-01", ("timestamp", "index_value"), "historical index price (separate Indices subscription)", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.BLOCKED_UNRESOLVED),
    _item(Capability.INTEREST_RATE_HISTORY, "causally published local model rate", Requirement.REQUIRED_NOW, Resolution.UNKNOWN, "project replay range (unresolved)", "UNKNOWN", ("reference_or_publication_datetime", "rate_value"), "rate history (source unresolved)", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.BLOCKED_UNRESOLVED),
    _item(Capability.CONTRACT_METADATA, "identify root, expiry, strike and right", Requirement.REQUIRED_NOW, Resolution.UNKNOWN, "project replay range (unresolved)", "UNKNOWN", ("root", "expiration", "strike", "right"), "option contract metadata", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.READY_WITH_CONSERVATIVE_RULE),
    _item(Capability.TRADE_QUOTE, "optional joined diagnostic", Requirement.OPTIONAL, Resolution.TICK, "diagnostic range only", "2016-01-01", ("timestamp", "price", "size", "bid", "ask", "contract_identity"), "historical option trade_quote", CausalStatus.BLOCKED_UNRESOLVED, MappingStatus.BLOCKED_UNRESOLVED),
)


def capability_contract(capability: Capability) -> CapabilityContract:
    return next(item for item in CAPABILITY_INVENTORY if item.capability is capability)


def _action(order: int, action: VerificationActionType, capability: Capability) -> VerificationAction:
    item = capability_contract(capability)
    scope = "one account metadata response" if action is VerificationActionType.READ_ACCOUNT_METADATA else "one symbol/root; one contract and one timestamp where supported"
    max_rows = 1 if action is not VerificationActionType.MINIMAL_SINGLE_DAY_PROBE else 10000
    return VerificationAction(order, action, capability, item.expected_endpoint_family, True, scope,
        max_rows, "one timestamp/smallest interval; one trading day only if smaller is unsupported",
        "SPX/SPXW; exact test contract selected only after authorization", item.required_fields,
        "explicit account metadata or accessible response with expected schema and bounded row count",
        "explicit provider entitlement error for this dataset",
        "empty response, transport/error outcome, HTTP success without fields, or unclear plan metadata",
        RetentionClass.METADATA_ONLY if action is VerificationActionType.READ_ACCOUNT_METADATA else RetentionClass.SCHEMA_SAMPLE,
        False)


ACCOUNT_VERIFICATION_PLAN: Tuple[VerificationAction, ...] = (
    _action(1, VerificationActionType.READ_ACCOUNT_METADATA, Capability.OPTIONS_CONTRACT_LIST),
    _action(2, VerificationActionType.MINIMAL_SCHEMA_PROBE, Capability.OPTIONS_CONTRACT_LIST),
    _action(3, VerificationActionType.MINIMAL_SINGLE_CONTRACT_PROBE, Capability.OPTION_QUOTES),
    _action(4, VerificationActionType.MINIMAL_SINGLE_CONTRACT_PROBE, Capability.OPTION_TRADES),
    _action(5, VerificationActionType.MINIMAL_SINGLE_CONTRACT_PROBE, Capability.OPTION_OPEN_INTEREST),
    _action(6, VerificationActionType.MINIMAL_SINGLE_CONTRACT_PROBE, Capability.OPTION_IV),
    _action(7, VerificationActionType.MINIMAL_SINGLE_CONTRACT_PROBE, Capability.OPTION_FIRST_ORDER_GREEKS),
    _action(8, VerificationActionType.MINIMAL_SINGLE_CONTRACT_PROBE, Capability.OPTION_EOD_GREEKS),
    _action(9, VerificationActionType.MINIMAL_SINGLE_TIMESTAMP_PROBE, Capability.SPX_INDEX_HISTORY),
    _action(10, VerificationActionType.MINIMAL_SINGLE_TIMESTAMP_PROBE, Capability.INTEREST_RATE_HISTORY),
)


def can_execute_verification_plan() -> bool:
    """A constant fail-closed authorization gate; no automatic promotion exists."""
    return CONTROLLED_ACCOUNT_VERIFICATION_AUTHORIZED
