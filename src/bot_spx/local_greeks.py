"""Offline, deterministic Black--Scholes contract for synthetic validation.

There is deliberately no transport, file, environment, or runtime integration in
this module.  Mathematical correctness does not imply historical replay
eligibility; :func:`greeks_reconstruction_eligibility` is a separate gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import erf, exp, isfinite, log, pi, sqrt


MODEL_VERSION = "LOCAL_SPX_BS_V1"
SOLVER_VERSION = "LOCAL_SPX_IV_BISECTION_V1"
PRICE_POLICY_VERSION = "MID_V1"
EXPIRATION_CONVENTION = "ACTUAL_SECONDS_OVER_365_DAYS_V1"
YEAR_SECONDS = 365 * 24 * 60 * 60
SIGMA_LOWER = 1e-8
SIGMA_UPPER = 5.0
IV_PRICE_TOLERANCE = 1e-10
IV_MAX_ITERATIONS = 200


class OptionRight(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class CalculationMode(str, Enum):
    MATHEMATICAL_TEST_ONLY = "MATHEMATICAL_TEST_ONLY"
    HISTORICAL_SPX_REPLAY = "HISTORICAL_SPX_REPLAY"


class ContractStatus(str, Enum):
    SOLVED = "SOLVED"
    NO_SOLUTION = "NO_SOLUTION"
    INVALID_INPUT = "INVALID_INPUT"
    NON_CAUSAL_INPUT = "NON_CAUSAL_INPUT"
    UNRESOLVED_POLICY = "UNRESOLVED_POLICY"


class EligibilityStatus(str, Enum):
    MATHEMATICAL_TEST_ONLY = "MATHEMATICAL_TEST_ONLY"
    BLOCKED_NON_CAUSAL_INPUT = "BLOCKED_NON_CAUSAL_INPUT"
    BLOCKED_UNRESOLVED_POLICY = "BLOCKED_UNRESOLVED_POLICY"
    ELIGIBLE_FOR_REPLAY = "ELIGIBLE_FOR_REPLAY"


class RatePolicy(str, Enum):
    LATEST_CAUSALLY_PUBLISHED_RATE = "LATEST_CAUSALLY_PUBLISHED_RATE"
    EXPLICIT_CAUSAL_RATE = "EXPLICIT_CAUSAL_RATE"
    VERSIONED_APPROVED_FALLBACK = "VERSIONED_APPROVED_FALLBACK"


class DividendPolicy(str, Enum):
    ZERO = "ZERO"
    EXPLICIT_ANNUAL_DIVIDEND = "EXPLICIT_ANNUAL_DIVIDEND"
    OTHER_VERSIONED_POLICY = "OTHER_VERSIONED_POLICY"


class PolicyState(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class TemporalInput:
    event_time: datetime
    available_time: datetime


@dataclass(frozen=True)
class InputProvenance:
    identifier: str
    source: str
    temporal: TemporalInput
    transformation: str = "raw"


@dataclass(frozen=True)
class LocalGreeksInput:
    right: OptionRight
    strike: float
    expiration_time: datetime
    replay_time: datetime
    bid: float | None
    ask: float | None
    underlying_price: float
    risk_free_rate: float
    dividend_yield: float
    option: InputProvenance
    underlying: InputProvenance
    rate: InputProvenance
    rate_reference_time: datetime
    rate_policy: RatePolicy
    dividend_policy: DividendPolicy
    quote_policy_state: PolicyState = PolicyState.RESOLVED
    underlying_staleness_state: PolicyState = PolicyState.RESOLVED
    underlying_alignment_policy: str = "SYNTHETIC_EXACT_TIME_ONLY"
    model_version: str = MODEL_VERSION
    real_spx_mapping_status: str = "BLOCKED_UNRESOLVED"


@dataclass(frozen=True)
class PriceSelectionResult:
    status: ContractStatus
    price: float | None
    reason: str | None
    policy_version: str = PRICE_POLICY_VERSION


@dataclass(frozen=True)
class EligibilityResult:
    status: EligibilityStatus
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class IVSolveResult:
    status: ContractStatus
    implied_volatility: float | None
    iterations: int
    reason: str | None
    solver_version: str = SOLVER_VERSION


@dataclass(frozen=True)
class ResultProvenance:
    model_version: str
    solver_version: str
    replay_time: datetime
    calculation_mode: CalculationMode
    option_input_identifier: str
    underlying_input_identifier: str
    rate_input_identifier: str
    bid: float
    ask: float
    selected_option_price: float
    option_price_policy: str
    underlying_price: float
    risk_free_rate: float
    dividend_yield: float
    dividend_policy: DividendPolicy
    rate_policy: RatePolicy
    expiration_time: datetime
    expiration_convention: str
    option_event_time: datetime
    option_available_time: datetime
    underlying_event_time: datetime
    underlying_available_time: datetime
    rate_reference_time: datetime
    rate_available_time: datetime
    transformations: tuple[str, ...]
    eligibility: EligibilityResult


@dataclass(frozen=True)
class LocalGreeksResult:
    status: ContractStatus
    implied_volatility: float | None
    price: float | None
    delta: float | None
    gamma: float | None
    vega_per_1_00_vol: float | None
    theta_per_year: float | None
    rho_per_1_00_rate: float | None
    provenance: ResultProvenance | None
    reason: str | None = None
    model_version: str = MODEL_VERSION


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def time_to_expiration(valuation_time: datetime, expiration_time: datetime) -> float | None:
    """Return exact elapsed UTC seconds / 31,536,000; ``None`` for naive inputs."""
    if not _aware(valuation_time) or not _aware(expiration_time):
        return None
    return (_utc(expiration_time) - _utc(valuation_time)).total_seconds() / YEAR_SECONDS


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _pdf(x: float) -> float:
    return exp(-0.5 * x * x) / sqrt(2.0 * pi)


def d1_d2(spot: float, strike: float, rate: float, dividend: float,
          volatility: float, years: float) -> tuple[float, float]:
    root_t = sqrt(years)
    d1 = (log(spot / strike) + (rate - dividend + 0.5 * volatility**2) * years) / (volatility * root_t)
    return d1, d1 - volatility * root_t


def black_scholes_price(right: OptionRight, spot: float, strike: float, rate: float,
                        dividend: float, volatility: float, years: float) -> float:
    """European option premium in index points; caller supplies valid inputs."""
    first, second = d1_d2(spot, strike, rate, dividend, volatility, years)
    discounted_spot = spot * exp(-dividend * years)
    discounted_strike = strike * exp(-rate * years)
    if right is OptionRight.CALL:
        return discounted_spot * _cdf(first) - discounted_strike * _cdf(second)
    return discounted_strike * _cdf(-second) - discounted_spot * _cdf(-first)


def black_scholes_greeks(right: OptionRight, spot: float, strike: float, rate: float,
                         dividend: float, volatility: float, years: float) -> tuple[float, float, float, float, float]:
    """Return delta, gamma, vega/1.00 vol, theta/year, rho/1.00 rate."""
    first, second = d1_d2(spot, strike, rate, dividend, volatility, years)
    root_t = sqrt(years)
    eq = exp(-dividend * years)
    er = exp(-rate * years)
    density = _pdf(first)
    gamma = eq * density / (spot * volatility * root_t)
    vega = spot * eq * density * root_t
    common_theta = -(spot * eq * density * volatility) / (2.0 * root_t)
    if right is OptionRight.CALL:
        delta = eq * _cdf(first)
        theta = common_theta - rate * strike * er * _cdf(second) + dividend * spot * eq * _cdf(first)
        rho = strike * years * er * _cdf(second)
    else:
        delta = eq * (_cdf(first) - 1.0)
        theta = common_theta + rate * strike * er * _cdf(-second) - dividend * spot * eq * _cdf(-first)
        rho = -strike * years * er * _cdf(-second)
    return delta, gamma, vega, theta, rho


def select_mid(bid: float | None, ask: float | None,
               *, quote_policy_state: PolicyState = PolicyState.RESOLVED) -> PriceSelectionResult:
    if quote_policy_state is PolicyState.UNRESOLVED:
        return PriceSelectionResult(ContractStatus.UNRESOLVED_POLICY, None, "quote spread/staleness policy unresolved")
    if bid is None or ask is None:
        return PriceSelectionResult(ContractStatus.INVALID_INPUT, None, "bid and ask are required")
    if not all(isinstance(x, (int, float)) and isfinite(x) for x in (bid, ask)):
        return PriceSelectionResult(ContractStatus.INVALID_INPUT, None, "bid and ask must be finite")
    if bid < 0 or ask < 0 or bid > ask:
        return PriceSelectionResult(ContractStatus.INVALID_INPUT, None, "quote is negative or crossed")
    mid = (bid + ask) / 2.0
    if not isfinite(mid) or mid < 0:
        return PriceSelectionResult(ContractStatus.INVALID_INPUT, None, "mid must be finite and non-negative")
    return PriceSelectionResult(ContractStatus.SOLVED, mid, None)


def no_arbitrage_bounds(right: OptionRight, spot: float, strike: float, rate: float,
                        dividend: float, years: float) -> tuple[float, float]:
    discounted_spot = spot * exp(-dividend * years)
    discounted_strike = strike * exp(-rate * years)
    if right is OptionRight.CALL:
        return max(0.0, discounted_spot - discounted_strike), discounted_spot
    return max(0.0, discounted_strike - discounted_spot), discounted_strike


def _mathematical_error(data: LocalGreeksInput) -> str | None:
    if not isinstance(data, LocalGreeksInput):
        return "LocalGreeksInput is required"
    timestamps = (data.expiration_time, data.replay_time, data.option.temporal.event_time,
                  data.option.temporal.available_time, data.underlying.temporal.event_time,
                  data.underlying.temporal.available_time, data.rate.temporal.event_time,
                  data.rate.temporal.available_time, data.rate_reference_time)
    if not all(_aware(value) for value in timestamps):
        return "all timestamps must be timezone-aware"
    numbers = (data.strike, data.underlying_price, data.risk_free_rate, data.dividend_yield)
    if not all(isinstance(x, (int, float)) and isfinite(x) for x in numbers):
        return "numeric inputs must be finite"
    if data.strike <= 0 or data.underlying_price <= 0:
        return "spot and strike must be positive"
    if data.model_version != MODEL_VERSION:
        return "unsupported model version"
    years = time_to_expiration(data.replay_time, data.expiration_time)
    if years is None or years <= 0:
        return "expiration must be strictly after replay_time"
    if abs(data.risk_free_rate * years) > 700 or abs(data.dividend_yield * years) > 700:
        return "discount exponent is outside the finite numerical domain"
    if data.dividend_policy is DividendPolicy.ZERO and data.dividend_yield != 0:
        return "ZERO dividend policy requires zero yield"
    return None


def greeks_reconstruction_eligibility(data: LocalGreeksInput,
                                      mode: CalculationMode) -> EligibilityResult:
    """Pure causal gate; the current real SPX route is intentionally blocked."""
    if mode is CalculationMode.MATHEMATICAL_TEST_ONLY:
        return EligibilityResult(EligibilityStatus.MATHEMATICAL_TEST_ONLY, ())
    unresolved: list[str] = []
    if data.real_spx_mapping_status == "BLOCKED_UNRESOLVED":
        unresolved.append("SPX_HISTORICAL_SPOT_MAPPING_BLOCKED_UNRESOLVED")
    if data.quote_policy_state is PolicyState.UNRESOLVED:
        unresolved.append("QUOTE_POLICY_UNRESOLVED")
    if data.underlying_staleness_state is PolicyState.UNRESOLVED:
        unresolved.append("UNDERLYING_STALENESS_POLICY_UNRESOLVED")
    if data.rate_policy is RatePolicy.VERSIONED_APPROVED_FALLBACK:
        unresolved.append("RATE_FALLBACK_POLICY_UNRESOLVED")
    if data.dividend_policy is DividendPolicy.OTHER_VERSIONED_POLICY:
        unresolved.append("DIVIDEND_POLICY_UNRESOLVED")
    if unresolved:
        return EligibilityResult(EligibilityStatus.BLOCKED_UNRESOLVED_POLICY, tuple(sorted(unresolved)))
    causal: list[str] = []
    if _aware(data.replay_time):
        replay = _utc(data.replay_time)
        for label, provenance in (("OPTION", data.option), ("UNDERLYING", data.underlying), ("RATE", data.rate)):
            if not _aware(provenance.temporal.available_time) or _utc(provenance.temporal.available_time) > replay:
                causal.append(f"{label}_AVAILABLE_AFTER_REPLAY")
            if not _aware(provenance.temporal.event_time) or _utc(provenance.temporal.event_time) > replay:
                causal.append(f"{label}_EVENT_AFTER_REPLAY")
        if not _aware(data.rate_reference_time) or _utc(data.rate_reference_time) > replay:
            causal.append("RATE_REFERENCE_AFTER_REPLAY")
    else:
        causal.append("REPLAY_TIME_NOT_TIMEZONE_AWARE")
    if causal:
        return EligibilityResult(EligibilityStatus.BLOCKED_NON_CAUSAL_INPUT, tuple(sorted(causal)))
    return EligibilityResult(EligibilityStatus.ELIGIBLE_FOR_REPLAY, ())


def solve_implied_volatility(data: LocalGreeksInput, *, max_iterations: int = IV_MAX_ITERATIONS) -> IVSolveResult:
    error = _mathematical_error(data)
    if error:
        return IVSolveResult(ContractStatus.INVALID_INPUT, None, 0, error)
    selected = select_mid(data.bid, data.ask, quote_policy_state=data.quote_policy_state)
    if selected.status is not ContractStatus.SOLVED:
        return IVSolveResult(selected.status, None, 0, selected.reason)
    if max_iterations < 1:
        return IVSolveResult(ContractStatus.NO_SOLUTION, None, 0, "solver iteration budget exhausted")
    assert selected.price is not None
    years = time_to_expiration(data.replay_time, data.expiration_time)
    assert years is not None
    lower_price, upper_price = no_arbitrage_bounds(data.right, data.underlying_price, data.strike,
                                                   data.risk_free_rate, data.dividend_yield, years)
    if selected.price < lower_price - IV_PRICE_TOLERANCE or selected.price > upper_price + IV_PRICE_TOLERANCE:
        return IVSolveResult(ContractStatus.INVALID_INPUT, None, 0, "premium violates European no-arbitrage bounds")
    price_at_low = black_scholes_price(data.right, data.underlying_price, data.strike,
                                       data.risk_free_rate, data.dividend_yield, SIGMA_LOWER, years)
    price_at_high = black_scholes_price(data.right, data.underlying_price, data.strike,
                                        data.risk_free_rate, data.dividend_yield, SIGMA_UPPER, years)
    if price_at_high - price_at_low <= IV_PRICE_TOLERANCE:
        return IVSolveResult(ContractStatus.NO_SOLUTION, None, 0, "premium does not identify volatility within tolerance")
    if selected.price < price_at_low - IV_PRICE_TOLERANCE or selected.price > price_at_high + IV_PRICE_TOLERANCE:
        return IVSolveResult(ContractStatus.NO_SOLUTION, None, 0, "solution lies outside configured volatility bounds")
    low, high = SIGMA_LOWER, SIGMA_UPPER
    for iteration in range(1, max_iterations + 1):
        mid = (low + high) / 2.0
        candidate = black_scholes_price(data.right, data.underlying_price, data.strike,
                                        data.risk_free_rate, data.dividend_yield, mid, years)
        if abs(candidate - selected.price) <= IV_PRICE_TOLERANCE:
            return IVSolveResult(ContractStatus.SOLVED, mid, iteration, None)
        if candidate < selected.price:
            low = mid
        else:
            high = mid
    return IVSolveResult(ContractStatus.NO_SOLUTION, None, max_iterations, "solver iteration budget exhausted")


def reconstruct_local_greeks(data: LocalGreeksInput, mode: CalculationMode) -> LocalGreeksResult:
    eligibility = greeks_reconstruction_eligibility(data, mode)
    if mode is CalculationMode.HISTORICAL_SPX_REPLAY and eligibility.status is not EligibilityStatus.ELIGIBLE_FOR_REPLAY:
        status = (ContractStatus.NON_CAUSAL_INPUT if eligibility.status is EligibilityStatus.BLOCKED_NON_CAUSAL_INPUT
                  else ContractStatus.UNRESOLVED_POLICY)
        return LocalGreeksResult(status, None, None, None, None, None, None, None, None,
                                 ";".join(eligibility.blocking_reasons))
    solved = solve_implied_volatility(data)
    if solved.status is not ContractStatus.SOLVED:
        return LocalGreeksResult(solved.status, None, None, None, None, None, None, None, None, solved.reason)
    selected = select_mid(data.bid, data.ask)
    assert solved.implied_volatility is not None and selected.price is not None
    years = time_to_expiration(data.replay_time, data.expiration_time)
    assert years is not None and data.bid is not None and data.ask is not None
    delta, gamma, vega, theta, rho = black_scholes_greeks(
        data.right, data.underlying_price, data.strike, data.risk_free_rate,
        data.dividend_yield, solved.implied_volatility, years)
    provenance = ResultProvenance(
        MODEL_VERSION, SOLVER_VERSION, data.replay_time, mode, data.option.identifier,
        data.underlying.identifier, data.rate.identifier, data.bid, data.ask, selected.price,
        PRICE_POLICY_VERSION, data.underlying_price, data.risk_free_rate, data.dividend_yield,
        data.dividend_policy, data.rate_policy, data.expiration_time, EXPIRATION_CONVENTION,
        data.option.temporal.event_time, data.option.temporal.available_time,
        data.underlying.temporal.event_time, data.underlying.temporal.available_time,
        data.rate_reference_time, data.rate.temporal.available_time,
        (data.option.transformation, data.underlying.transformation, data.rate.transformation,
         "mid=(bid+ask)/2", "black-scholes", "iv-bisection"), eligibility)
    return LocalGreeksResult(ContractStatus.SOLVED, solved.implied_volatility, selected.price,
                             delta, gamma, vega, theta, rho, provenance)
