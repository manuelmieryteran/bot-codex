"""Pure, synthetic-only causal input contract for local SPX Greeks.

This module intentionally has no loaders or operational side effects.  In
particular, an exchange timestamp is not evidence of historical availability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Any

from .local_greeks import (
    CalculationMode, DividendPolicy, InputProvenance, LocalGreeksInput,
    OptionRight, PolicyState, RatePolicy, TemporalInput,
    reconstruct_local_greeks,
)


class InputKind(str, Enum):
    OPTION_QUOTE = "OPTION_QUOTE"
    UNDERLYING_SPX = "UNDERLYING_SPX"
    RATE = "RATE"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    BLOCKED_MAPPING = "BLOCKED_MAPPING"
    BLOCKED_UNRESOLVED_AVAILABILITY = "BLOCKED_UNRESOLVED_AVAILABILITY"
    BLOCKED_FUTURE_EVENT = "BLOCKED_FUTURE_EVENT"
    BLOCKED_FUTURE_AVAILABILITY = "BLOCKED_FUTURE_AVAILABILITY"
    BLOCKED_CORRECTION_POLICY = "BLOCKED_CORRECTION_POLICY"
    BLOCKED_ALIGNMENT = "BLOCKED_ALIGNMENT"
    BLOCKED_STALENESS_POLICY = "BLOCKED_STALENESS_POLICY"
    BLOCKED_UNRESOLVED_POLICY = "BLOCKED_UNRESOLVED_POLICY"
    BLOCKED_MISSING = "BLOCKED_MISSING"
    INVALID_INPUT = "INVALID_INPUT"
    MATHEMATICAL_TEST_ONLY = "MATHEMATICAL_TEST_ONLY"


class MappingStatus(str, Enum):
    SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"
    BLOCKED_UNRESOLVED = "BLOCKED_UNRESOLVED"


class QualityStatus(str, Enum):
    VALID = "VALID"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"


class CorrectionStatus(str, Enum):
    POINT_IN_TIME = "POINT_IN_TIME"
    UNRESOLVED = "UNRESOLVED"
    CORRECTED_LINKED = "CORRECTED_LINKED"


class Missingness(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    ZERO = "ZERO"
    NO_MESSAGE = "NO_MESSAGE"
    UNKNOWN = "UNKNOWN"


class StalenessPolicy(str, Enum):
    NO_THRESHOLD_APPROVED = "NO_THRESHOLD_APPROVED"
    EXPLICIT_TEST_THRESHOLD = "EXPLICIT_TEST_THRESHOLD"
    FUTURE_APPROVED_THRESHOLD = "FUTURE_APPROVED_THRESHOLD"


class AlignmentMethod(str, Enum):
    LAST_CAUSALLY_AVAILABLE = "LAST_CAUSALLY_AVAILABLE"
    EXACT_SYNTHETIC = "EXACT_SYNTHETIC"
    NEAREST_FUTURE = "NEAREST_FUTURE"
    FUTURE_INTERPOLATION = "FUTURE_INTERPOLATION"
    FUTURE_BACKFILL = "FUTURE_BACKFILL"


class MetadataStatus(str, Enum):
    SYNTHETIC_COMPLETE = "SYNTHETIC_COMPLETE"
    CONSERVATIVE_SPXW = "CONSERVATIVE_SPXW"
    INCOMPLETE = "INCOMPLETE"
    SPECIAL_CASE_UNRESOLVED = "SPECIAL_CASE_UNRESOLVED"


class DividendEvidencePolicy(str, Enum):
    ZERO = "ZERO"
    EXPLICIT_ANNUAL_DIVIDEND = "EXPLICIT_ANNUAL_DIVIDEND"
    OTHER_VERSIONED_POLICY = "OTHER_VERSIONED_POLICY"


@dataclass(frozen=True)
class CausalInputProvenance:
    source: str
    identifier: str
    correction_semantics: str
    original_persists: bool | None = None
    correction_link_exists: bool | None = None


@dataclass(frozen=True)
class CausalInputObservation:
    input_kind: InputKind
    value: Any
    unit: str
    event_time: datetime
    source_time: datetime
    available_time: datetime | None
    replay_time: datetime
    source: str
    identifier: str
    sequence: int | None
    correction_status: CorrectionStatus
    quality_status: QualityStatus
    staleness_policy: StalenessPolicy
    provenance: CausalInputProvenance
    mapping_status: MappingStatus
    missingness: Missingness = Missingness.PRESENT
    test_max_age: timedelta | None = None


@dataclass(frozen=True)
class OptionQuoteValue:
    bid: float
    ask: float
    contract_identity: str
    bid_size: int | None = None
    ask_size: int | None = None
    condition: str | None = None


@dataclass(frozen=True)
class RateValue:
    rate: float
    reference_time: datetime
    publication_time: datetime | None
    policy: RatePolicy
    policy_version: str


@dataclass(frozen=True)
class DividendInput:
    value: float
    policy: DividendEvidencePolicy
    policy_version: str | None
    approved_for_real_replay: bool = False


@dataclass(frozen=True)
class ContractMetadata:
    root: str
    expiration: date
    expiration_time: datetime
    strike: float
    right: OptionRight
    settlement_style: str | None
    contract_identity: str
    source: str
    reference_time: datetime
    available_time: datetime | None
    provenance: str
    status: MetadataStatus


@dataclass(frozen=True)
class CausalEligibilityResult:
    status: EligibilityStatus
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlignmentResult:
    eligibility: CausalEligibilityResult
    method: AlignmentMethod
    event_time_skew: timedelta | None
    available_time_skew: timedelta | None


@dataclass(frozen=True)
class CausalGreeksInputBundle:
    replay_time: datetime
    option: CausalInputObservation
    underlying: CausalInputObservation
    rate: CausalInputObservation
    dividend: DividendInput
    metadata: ContractMetadata
    alignment: AlignmentResult
    eligibility: CausalEligibilityResult


@dataclass(frozen=True)
class BundleBuildResult:
    eligibility: CausalEligibilityResult
    bundle: CausalGreeksInputBundle | None


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def evaluate_observation(observation: CausalInputObservation | None, *, test_only: bool) -> CausalEligibilityResult:
    """Evaluate one observation without synthesizing availability or filling gaps."""
    if observation is None or observation.missingness in {Missingness.MISSING, Missingness.NO_MESSAGE, Missingness.UNKNOWN}:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_MISSING, ("observation is absent",))
    timestamps = (observation.event_time, observation.source_time, observation.replay_time)
    if not all(_aware(item) for item in timestamps) or (
        observation.available_time is not None and not _aware(observation.available_time)
    ):
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("timestamps must be timezone-aware",))
    if observation.mapping_status is MappingStatus.BLOCKED_UNRESOLVED:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_MAPPING, ("real mapping remains BLOCKED_UNRESOLVED",))
    if observation.available_time is None:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_AVAILABILITY,
                                       ("available_time requires direct contractual evidence",))
    if _utc(observation.event_time) > _utc(observation.replay_time):
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_FUTURE_EVENT, ("event_time is after replay_time",))
    if _utc(observation.available_time) > _utc(observation.replay_time):
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY,
                                       ("available_time is after replay_time",))
    if observation.correction_status is CorrectionStatus.UNRESOLVED:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_CORRECTION_POLICY,
                                       ("point-in-time correction semantics unresolved",))
    if observation.quality_status is not QualityStatus.VALID:
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("quality is not valid",))
    if observation.staleness_policy is StalenessPolicy.NO_THRESHOLD_APPROVED:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_STALENESS_POLICY,
                                       ("no staleness threshold is approved",))
    if observation.staleness_policy is StalenessPolicy.EXPLICIT_TEST_THRESHOLD:
        if not test_only or observation.test_max_age is None:
            return CausalEligibilityResult(EligibilityStatus.BLOCKED_STALENESS_POLICY,
                                           ("test threshold is only valid in test-only mode",))
        if observation.replay_time - observation.event_time > observation.test_max_age:
            return CausalEligibilityResult(EligibilityStatus.BLOCKED_STALENESS_POLICY,
                                           ("synthetic observation exceeds test threshold",))
    return CausalEligibilityResult(EligibilityStatus.ELIGIBLE)


def align_inputs(option: CausalInputObservation, underlying: CausalInputObservation,
                 method: AlignmentMethod) -> AlignmentResult:
    """Represent both cross-feed clocks; equality does not imply simultaneity."""
    event_skew = (option.event_time - underlying.event_time) if _aware(option.event_time) and _aware(underlying.event_time) else None
    available_skew = None
    if _aware(option.available_time) and _aware(underlying.available_time):
        available_skew = option.available_time - underlying.available_time  # type: ignore[operator]
    if method in {AlignmentMethod.NEAREST_FUTURE, AlignmentMethod.FUTURE_INTERPOLATION,
                  AlignmentMethod.FUTURE_BACKFILL}:
        return AlignmentResult(CausalEligibilityResult(EligibilityStatus.BLOCKED_ALIGNMENT,
                               (f"{method.value} is prohibited",)), method, event_skew, available_skew)
    return AlignmentResult(CausalEligibilityResult(EligibilityStatus.ELIGIBLE), method,
                           event_skew, available_skew)


def _metadata_gate(metadata: ContractMetadata | None, replay_time: datetime, *, test_only: bool) -> CausalEligibilityResult:
    if metadata is None:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_MISSING, ("contract metadata missing",))
    times = (metadata.expiration_time, metadata.reference_time, replay_time)
    if not all(_aware(value) for value in times) or (metadata.available_time is not None and not _aware(metadata.available_time)):
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("metadata timestamps must be aware",))
    if metadata.available_time is None:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_AVAILABILITY)
    if _utc(metadata.reference_time) > _utc(replay_time):
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_FUTURE_EVENT)
    if _utc(metadata.available_time) > _utc(replay_time):
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY)
    if metadata.status in {MetadataStatus.INCOMPLETE, MetadataStatus.SPECIAL_CASE_UNRESOLVED}:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_POLICY,
                                       ("historical metadata is incomplete or a special case",))
    if not metadata.contract_identity or metadata.strike <= 0 or metadata.expiration != replay_time.date():
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("0DTE identity/date/strike invalid",))
    if metadata.status is MetadataStatus.CONSERVATIVE_SPXW and metadata.root != "SPXW":
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT)
    return CausalEligibilityResult(EligibilityStatus.ELIGIBLE)


def _rate_gate(rate: CausalInputObservation, replay_time: datetime) -> CausalEligibilityResult:
    if not isinstance(rate.value, RateValue):
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("RateValue required",))
    value = rate.value
    if not _aware(value.reference_time) or value.publication_time is None:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_AVAILABILITY,
                                       ("publication_time is required",))
    if not _aware(value.publication_time):
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT)
    if _utc(value.publication_time) > _utc(replay_time):
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_FUTURE_AVAILABILITY,
                                       ("rate was not yet published",))
    if value.policy is RatePolicy.VERSIONED_APPROVED_FALLBACK:
        return CausalEligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_POLICY,
                                       ("rate fallback is not approved",))
    if not isfinite(value.rate):
        return CausalEligibilityResult(EligibilityStatus.INVALID_INPUT)
    return CausalEligibilityResult(EligibilityStatus.ELIGIBLE)


def build_causal_greeks_input_bundle(*, replay_time: datetime,
        option: CausalInputObservation | None, underlying: CausalInputObservation | None,
        rate: CausalInputObservation | None, dividend: DividendInput | None,
        metadata: ContractMetadata | None, alignment_method: AlignmentMethod,
        test_only: bool = False) -> BundleBuildResult:
    """Build an all-or-nothing bundle from already-loaded immutable observations."""
    if not _aware(replay_time):
        result = CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("replay_time must be aware",))
        return BundleBuildResult(result, None)
    for label, observation in (("option", option), ("underlying", underlying), ("rate", rate)):
        gate = evaluate_observation(observation, test_only=test_only)
        if gate.status is not EligibilityStatus.ELIGIBLE:
            return BundleBuildResult(CausalEligibilityResult(gate.status,
                                     tuple(f"{label}: {reason}" for reason in gate.reasons) or (label,)), None)
    assert option is not None and underlying is not None and rate is not None
    if not isinstance(option.value, OptionQuoteValue) or option.input_kind is not InputKind.OPTION_QUOTE:
        return BundleBuildResult(CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("option quote value required",)), None)
    if option.value.bid < 0 or option.value.ask < option.value.bid:
        return BundleBuildResult(CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("invalid bid/ask",)), None)
    if underlying.input_kind is not InputKind.UNDERLYING_SPX or not isinstance(underlying.value, (float, int)) or underlying.value <= 0:
        return BundleBuildResult(CausalEligibilityResult(EligibilityStatus.INVALID_INPUT, ("positive SPX value required",)), None)
    rate_gate = _rate_gate(rate, replay_time)
    if rate_gate.status is not EligibilityStatus.ELIGIBLE:
        return BundleBuildResult(rate_gate, None)
    if dividend is None:
        return BundleBuildResult(CausalEligibilityResult(EligibilityStatus.BLOCKED_MISSING, ("dividend policy missing",)), None)
    if dividend.policy is DividendEvidencePolicy.ZERO and (dividend.value != 0 or (not test_only and not dividend.approved_for_real_replay)):
        status = EligibilityStatus.INVALID_INPUT if dividend.value != 0 else EligibilityStatus.BLOCKED_UNRESOLVED_POLICY
        return BundleBuildResult(CausalEligibilityResult(status, ("ZERO is mathematical-only unless approved",)), None)
    if dividend.policy is DividendEvidencePolicy.OTHER_VERSIONED_POLICY and not dividend.approved_for_real_replay:
        return BundleBuildResult(CausalEligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_POLICY,
                                 ("dividend policy not approved",)), None)
    metadata_gate = _metadata_gate(metadata, replay_time, test_only=test_only)
    if metadata_gate.status is not EligibilityStatus.ELIGIBLE:
        return BundleBuildResult(metadata_gate, None)
    assert metadata is not None
    if option.value.contract_identity != metadata.contract_identity:
        return BundleBuildResult(CausalEligibilityResult(EligibilityStatus.BLOCKED_ALIGNMENT,
                                 ("contract identities differ",)), None)
    alignment = align_inputs(option, underlying, alignment_method)
    if alignment.eligibility.status is not EligibilityStatus.ELIGIBLE:
        return BundleBuildResult(alignment.eligibility, None)
    status = EligibilityStatus.MATHEMATICAL_TEST_ONLY if test_only else EligibilityStatus.ELIGIBLE
    eligibility = CausalEligibilityResult(status)
    bundle = CausalGreeksInputBundle(replay_time, option, underlying, rate, dividend,
                                    metadata, alignment, eligibility)
    return BundleBuildResult(eligibility, bundle)


def to_local_greeks_input(bundle: CausalGreeksInputBundle) -> LocalGreeksInput:
    """Pure bridge; reject every blocked bundle rather than running silently."""
    if bundle.eligibility.status not in {EligibilityStatus.ELIGIBLE, EligibilityStatus.MATHEMATICAL_TEST_ONLY}:
        raise ValueError("blocked causal bundle cannot enter LOCAL_SPX_BS_V1")
    quote = bundle.option.value
    rate = bundle.rate.value
    assert isinstance(quote, OptionQuoteValue) and isinstance(rate, RateValue)
    def provenance(value: CausalInputObservation) -> InputProvenance:
        assert value.available_time is not None
        return InputProvenance(value.identifier, value.source,
                               TemporalInput(value.event_time, value.available_time))
    return LocalGreeksInput(
        bundle.metadata.right, bundle.metadata.strike, bundle.metadata.expiration_time,
        bundle.replay_time, quote.bid, quote.ask, float(bundle.underlying.value), rate.rate,
        bundle.dividend.value, provenance(bundle.option), provenance(bundle.underlying),
        provenance(bundle.rate), rate.reference_time, rate.policy,
        DividendPolicy.ZERO if bundle.dividend.policy is DividendEvidencePolicy.ZERO else DividendPolicy.EXPLICIT_ANNUAL_DIVIDEND,
        PolicyState.RESOLVED, PolicyState.RESOLVED, bundle.alignment.method.value,
        real_spx_mapping_status="SYNTHETIC_TEST_ONLY" if bundle.eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY else "CAUSALLY_APPROVED",
    )


def execute_local_greeks(bundle: CausalGreeksInputBundle):
    """Explicit gated test bridge; it is not imported by either runtime."""
    mode = (CalculationMode.MATHEMATICAL_TEST_ONLY
            if bundle.eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
            else CalculationMode.HISTORICAL_SPX_REPLAY)
    return reconstruct_local_greeks(to_local_greeks_input(bundle), mode)


def real_historical_spx_local_greeks_eligibility() -> CausalEligibilityResult:
    """Current immutable checkpoint: real option and SPX mappings remain blocked."""
    return CausalEligibilityResult(EligibilityStatus.BLOCKED_MAPPING,
        ("option_quotes=BLOCKED_UNRESOLVED", "spx_historical_spot=BLOCKED_UNRESOLVED"))
