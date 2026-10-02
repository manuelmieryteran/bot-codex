"""Synthetic-only contract tests; no provider output is used as an oracle."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import ast
import hashlib
import math
from pathlib import Path

import pytest

from bot_spx.historical_provider_spec import DecisionStatus, HUMAN_MAPPING_DECISIONS
from bot_spx.local_greeks import (
    EXPIRATION_CONVENTION, MODEL_VERSION, PRICE_POLICY_VERSION, SOLVER_VERSION,
    CalculationMode, ContractStatus, DividendPolicy, EligibilityStatus,
    InputProvenance, LocalGreeksInput, OptionRight, PolicyState, RatePolicy,
    TemporalInput, black_scholes_greeks, black_scholes_price,
    greeks_reconstruction_eligibility, reconstruct_local_greeks, select_mid,
    solve_implied_volatility, time_to_expiration,
)


UTC = timezone.utc
NOW = datetime(2024, 1, 2, 15, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]


def provenance(identifier, available=NOW, event=NOW):
    return InputProvenance(identifier, "SYNTHETIC_FIXTURE", TemporalInput(event, available))


def sample(*, right=OptionRight.CALL, strike=100.0, spot=100.0, rate=0.05,
           dividend=0.0, years=1.0, sigma=0.2, bid=None, ask=None, **changes):
    expiration = NOW + timedelta(seconds=years * 365 * 24 * 60 * 60)
    price = black_scholes_price(right, spot, strike, rate, dividend, sigma, years)
    values = dict(
        right=right, strike=strike, expiration_time=expiration, replay_time=NOW,
        bid=price if bid is None else bid, ask=price if ask is None else ask,
        underlying_price=spot, risk_free_rate=rate, dividend_yield=dividend,
        option=provenance("option-1"), underlying=provenance("underlying-1"),
        rate=provenance("rate-1"), rate_reference_time=NOW - timedelta(days=1),
        rate_policy=RatePolicy.EXPLICIT_CAUSAL_RATE,
        dividend_policy=(DividendPolicy.ZERO if dividend == 0 else DividendPolicy.EXPLICIT_ANNUAL_DIVIDEND),
    )
    if "rate_provenance" in changes:
        values["rate"] = changes.pop("rate_provenance")
    values.update(changes)
    return LocalGreeksInput(**values)


def test_versions_and_records_are_immutable():
    assert (MODEL_VERSION, SOLVER_VERSION, PRICE_POLICY_VERSION) == (
        "LOCAL_SPX_BS_V1", "LOCAL_SPX_IV_BISECTION_V1", "MID_V1")
    with pytest.raises(FrozenInstanceError):
        sample().strike = 101


def test_independent_reference_prices_and_all_greeks():
    # Published textbook S=K=100, r=5%, q=0, sigma=20%, T=1 reference values.
    call = black_scholes_price(OptionRight.CALL, 100, 100, .05, 0, .2, 1)
    put = black_scholes_price(OptionRight.PUT, 100, 100, .05, 0, .2, 1)
    assert call == pytest.approx(10.4505835722, abs=1e-9)
    assert put == pytest.approx(5.5735260223, abs=1e-9)
    c = black_scholes_greeks(OptionRight.CALL, 100, 100, .05, 0, .2, 1)
    p = black_scholes_greeks(OptionRight.PUT, 100, 100, .05, 0, .2, 1)
    assert c == pytest.approx((.6368306512, .0187620173, 37.52403469, -6.414027546, 53.23248155), rel=3e-9)
    assert p == pytest.approx((-.3631693488, .0187620173, 37.52403469, -1.657880424, -41.89046090), rel=3e-9)


@pytest.mark.parametrize("right,strike", [
    (OptionRight.CALL, 80), (OptionRight.CALL, 100), (OptionRight.CALL, 120),
    (OptionRight.PUT, 80), (OptionRight.PUT, 100), (OptionRight.PUT, 120),
])
def test_itm_atm_otm_ranges_and_positive_gamma_vega(right, strike):
    delta, gamma, vega, theta, rho = black_scholes_greeks(right, 100, strike, .03, .01, .35, .25)
    assert (-1 <= delta <= 0) if right is OptionRight.PUT else (0 <= delta <= 1)
    assert gamma >= 0 and vega >= 0
    assert all(math.isfinite(x) for x in (delta, gamma, vega, theta, rho))


def test_put_call_parity_and_price_monotonicity():
    args = (100, 105, .04, .015)
    call = black_scholes_price(OptionRight.CALL, *args, .25, .3)
    put = black_scholes_price(OptionRight.PUT, *args, .25, .3)
    assert call - put == pytest.approx(100 * math.exp(-.015 * .3) - 105 * math.exp(-.04 * .3), abs=1e-12)
    assert black_scholes_price(OptionRight.CALL, *args, .50, .3) > call
    assert black_scholes_price(OptionRight.PUT, *args, .50, .3) > put


def test_greek_units_have_no_hidden_factor_100_or_multiplier():
    _, _, vega, theta, rho = black_scholes_greeks(OptionRight.CALL, 100, 100, .05, 0, .2, 1)
    assert vega / 100 == pytest.approx(.3752403469)  # one vol-point
    assert theta / 365 == pytest.approx(-.0175726782)  # one calendar day
    assert rho / 100 == pytest.approx(.5323248155)  # one rate-point
    assert vega != pytest.approx(vega * 100)  # no contract multiplier


@pytest.mark.parametrize("hour,minute,seconds", [(9, 30, 22500), (12, 0, 13500), (15, 30, 900), (15, 45, 0)])
def test_intraday_time_convention(hour, minute, seconds):
    valuation = datetime(2024, 6, 3, hour, minute, tzinfo=UTC)
    expiration = datetime(2024, 6, 3, 15, 45, tzinfo=UTC)
    assert time_to_expiration(valuation, expiration) == seconds / (365 * 86400)
    assert EXPIRATION_CONVENTION == "ACTUAL_SECONDS_OVER_365_DAYS_V1"


def test_exact_and_post_expiration_fail_closed_and_naive_is_invalid():
    exact = sample(expiration_time=NOW)
    post = sample(expiration_time=NOW - timedelta(seconds=1))
    naive = sample(replay_time=NOW.replace(tzinfo=None))
    assert solve_implied_volatility(exact).status is ContractStatus.INVALID_INPUT
    assert solve_implied_volatility(post).status is ContractStatus.INVALID_INPUT
    assert solve_implied_volatility(naive).status is ContractStatus.INVALID_INPUT


@pytest.mark.parametrize("right,strike,years,rate,sigma", [
    (OptionRight.CALL, 100, 1 / 365, 0, .08), (OptionRight.CALL, 100, .1, .03, .2),
    (OptionRight.CALL, 120, 1, .08, .8), (OptionRight.PUT, 80, .5, -.01, .15),
    (OptionRight.PUT, 100, 2, .05, .4), (OptionRight.PUT, 120, 1 / 12, .02, 1.2),
])
def test_iv_round_trip_matrix_is_deterministic(right, strike, years, rate, sigma):
    data = sample(right=right, strike=strike, years=years, rate=rate, sigma=sigma)
    first = solve_implied_volatility(data)
    second = solve_implied_volatility(data)
    assert first == second
    assert first.status is ContractStatus.SOLVED
    assert first.implied_volatility == pytest.approx(sigma, abs=2e-8)


@pytest.mark.parametrize("bid,ask,status", [
    (None, 1, ContractStatus.INVALID_INPUT), (1, None, ContractStatus.INVALID_INPUT),
    (-1, 1, ContractStatus.INVALID_INPUT), (2, 1, ContractStatus.INVALID_INPUT),
    (math.nan, 1, ContractStatus.INVALID_INPUT), (0, 0, ContractStatus.SOLVED),
    (0, 1, ContractStatus.SOLVED), (1, 1, ContractStatus.SOLVED),
])
def test_mid_policy_missing_crossed_nonfinite_zero_and_locked(bid, ask, status):
    result = select_mid(bid, ask)
    assert result.status is status
    if status is ContractStatus.SOLVED:
        assert result.price == (bid + ask) / 2


def test_unresolved_spread_or_staleness_has_no_invented_threshold():
    assert select_mid(0, 1000, quote_policy_state=PolicyState.UNRESOLVED).status is ContractStatus.UNRESOLVED_POLICY
    data = sample(underlying_staleness_state=PolicyState.UNRESOLVED)
    gate = greeks_reconstruction_eligibility(data, CalculationMode.HISTORICAL_SPX_REPLAY)
    assert gate.status is EligibilityStatus.BLOCKED_UNRESOLVED_POLICY
    assert "UNDERLYING_STALENESS_POLICY_UNRESOLVED" in gate.blocking_reasons


@pytest.mark.parametrize("right,bid,ask", [
    (OptionRight.CALL, 101, 101), (OptionRight.PUT, 101, 101),
])
def test_impossible_arbitrage_premium_is_invalid(right, bid, ask):
    assert solve_implied_volatility(sample(right=right, rate=0, bid=bid, ask=ask)).status is ContractStatus.INVALID_INPUT


def test_inside_arbitrage_bounds_but_above_sigma_cap_has_no_solution():
    # ATM one-day premium of 99 is below the broad call upper bound but unreachable at sigma <= 5.
    result = solve_implied_volatility(sample(years=1 / 365, rate=0, bid=99, ask=99))
    assert result.status is ContractStatus.NO_SOLUTION
    assert result.implied_volatility is None


def test_solver_exhaustion_is_explicit():
    result = solve_implied_volatility(sample(sigma=.234567), max_iterations=1)
    assert result.status is ContractStatus.NO_SOLUTION
    assert result.iterations == 1


@pytest.mark.parametrize("field,value", [
    ("underlying_price", 0), ("underlying_price", math.inf), ("strike", -1),
    ("risk_free_rate", math.nan), ("dividend_yield", math.inf),
])
def test_invalid_and_nonfinite_numeric_inputs(field, value):
    assert solve_implied_volatility(replace(sample(), **{field: value})).status is ContractStatus.INVALID_INPUT


@pytest.mark.parametrize("name", ["option", "underlying", "rate"])
def test_each_future_input_is_non_causal(name):
    key = "rate_provenance" if name == "rate" else name
    changed = {key: provenance(name, available=NOW + timedelta(microseconds=1))}
    data = sample(real_spx_mapping_status="READY", **changed)
    gate = greeks_reconstruction_eligibility(data, CalculationMode.HISTORICAL_SPX_REPLAY)
    assert gate.status is EligibilityStatus.BLOCKED_NON_CAUSAL_INPUT
    assert f"{name.upper()}_AVAILABLE_AFTER_REPLAY" in gate.blocking_reasons
    result = reconstruct_local_greeks(data, CalculationMode.HISTORICAL_SPX_REPLAY)
    assert result.status is ContractStatus.NON_CAUSAL_INPUT


def test_real_spx_route_cannot_be_replay_eligible():
    gate = greeks_reconstruction_eligibility(sample(), CalculationMode.HISTORICAL_SPX_REPLAY)
    assert gate.status is EligibilityStatus.BLOCKED_UNRESOLVED_POLICY
    assert gate.blocking_reasons == ("SPX_HISTORICAL_SPOT_MAPPING_BLOCKED_UNRESOLVED",)


def test_rate_fallback_and_other_dividend_remain_unresolved():
    data = sample(real_spx_mapping_status="READY",
                  rate_policy=RatePolicy.VERSIONED_APPROVED_FALLBACK,
                  dividend_policy=DividendPolicy.OTHER_VERSIONED_POLICY)
    gate = greeks_reconstruction_eligibility(data, CalculationMode.HISTORICAL_SPX_REPLAY)
    assert gate.status is EligibilityStatus.BLOCKED_UNRESOLVED_POLICY
    assert gate.blocking_reasons == tuple(sorted(gate.blocking_reasons))


def test_synthetic_result_has_reproducible_provenance_but_not_replay_eligibility():
    result = reconstruct_local_greeks(sample(dividend=.01), CalculationMode.MATHEMATICAL_TEST_ONLY)
    assert result.status is ContractStatus.SOLVED
    assert result.model_version == MODEL_VERSION
    assert result.provenance is not None
    p = result.provenance
    assert (p.model_version, p.solver_version, p.option_price_policy) == (MODEL_VERSION, SOLVER_VERSION, PRICE_POLICY_VERSION)
    assert (p.option_input_identifier, p.underlying_input_identifier, p.rate_input_identifier) == (
        "option-1", "underlying-1", "rate-1")
    assert p.eligibility.status is EligibilityStatus.MATHEMATICAL_TEST_ONLY
    assert p.selected_option_price == pytest.approx(result.price)
    assert "iv-bisection" in p.transformations


@pytest.mark.parametrize("right,strike,sigma", [
    (OptionRight.CALL, 100, .05), (OptionRight.CALL, 50, .2),
    (OptionRight.CALL, 150, 2), (OptionRight.PUT, 50, 5),
    (OptionRight.PUT, 100, 1), (OptionRight.PUT, 150, .05),
])
def test_zero_dte_approach_is_finite_or_explicit_no_solution(right, strike, sigma):
    data = sample(right=right, strike=strike, years=1 / (365 * 24 * 60), rate=0, sigma=sigma)
    result = solve_implied_volatility(data)
    assert result.status in {ContractStatus.SOLVED, ContractStatus.NO_SOLUTION}
    if result.status is ContractStatus.SOLVED:
        assert result.implied_volatility is not None
        assert math.isfinite(result.implied_volatility) and result.implied_volatility >= 0


def test_high_and_very_low_premium_cases_are_controlled():
    low = solve_implied_volatility(sample(years=1 / 365, rate=0, bid=1e-12, ask=1e-12))
    high = solve_implied_volatility(sample(years=1 / 365, rate=0, bid=99, ask=99))
    assert low.status in {ContractStatus.SOLVED, ContractStatus.NO_SOLUTION}
    assert high.status is ContractStatus.NO_SOLUTION


def test_no_network_or_operational_capability_in_module():
    source = (ROOT / "src/bot_spx/local_greeks.py").read_text()
    tree = ast.parse(source)
    imports = {node.module.split(".")[0] for node in ast.walk(tree)
               if isinstance(node, ast.ImportFrom) and node.module != "__future__"}
    imports |= {alias.name.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names}
    assert imports <= {"dataclasses", "datetime", "enum", "math"}
    forbidden = ("requests", "urllib", "http", "socket", "dotenv", "subprocess", "open(", "getenv")
    assert not any(term in source for term in forbidden)


def test_provider_and_local_mapping_decisions_remain_unchanged():
    decisions = {row.subject: row.status for row in HUMAN_MAPPING_DECISIONS}
    assert len(decisions) == 9
    assert decisions["provider_historical_greeks_iv"] is DecisionStatus.EXCLUDED
    assert decisions["locally_reconstructed_greeks_iv"] is DecisionStatus.NEEDS_RECONSTRUCTION
    for subject in ("open_interest", "option_trades", "option_quotes", "spx_historical_spot"):
        assert decisions[subject] is DecisionStatus.BLOCKED_UNRESOLVED


def test_protected_runtimes_unchanged_and_do_not_import_local_module():
    expected = {
        "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py": "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023",
        "spx_data_FASE5.py": "5527f41cd20f5e383ba0957c26a4bd250037c0b2502a3b047797799b1102aed6",
    }
    for filename, digest in expected.items():
        content = (ROOT / filename).read_bytes()
        assert hashlib.sha256(content).hexdigest() == digest
        assert b"local_greeks" not in content
