# FASE 5C-4B.4A — Local Greeks / IV causal reconstruction contract

## Scope and immutable model

`LOCAL_SPX_BS_V1` is an offline European Black–Scholes implementation for
synthetic numerical validation. It is not claimed to equal ThetaData, Cboe,
SpotGamma, or any other provider. It performs no I/O and is not imported by the
Phase 4 or Phase 5 runtimes. Mathematical correctness and causal replay
eligibility are independent gates. This phase does **not** authorize real data,
mapping promotion, backtesting, execution, or cutover.

## Equations

For spot \(S\), strike \(K\), continuously compounded rate \(r\), continuous
dividend yield \(q\), decimal annual volatility \(\sigma\), and years \(T>0\):

```
d1 = [ln(S/K) + (r - q + sigma^2/2) T] / (sigma sqrt(T))
d2 = d1 - sigma sqrt(T)
C  = S exp(-qT) N(d1) - K exp(-rT) N(d2)
P  = K exp(-rT) N(-d2) - S exp(-qT) N(-d1)
Delta_call = exp(-qT) N(d1)
Delta_put  = exp(-qT) [N(d1) - 1]
Gamma = exp(-qT) n(d1) / [S sigma sqrt(T)]
Vega  = S exp(-qT) n(d1) sqrt(T)
Theta_call = -S exp(-qT)n(d1)sigma/(2sqrt(T))
             - rK exp(-rT)N(d2) + qS exp(-qT)N(d1)
Theta_put  = -S exp(-qT)n(d1)sigma/(2sqrt(T))
             + rK exp(-rT)N(-d2) - qS exp(-qT)N(-d1)
Rho_call = KT exp(-rT)N(d2)
Rho_put  = -KT exp(-rT)N(-d2)
```

`N` and `n` are the standard-normal CDF and density. Implied volatility is the
unique in-range sigma whose model price equals the selected premium, found by
deterministic bisection.

## Units

Spot, strike, and premium are index points. Volatility, rate, and dividend yield
are annual decimal fractions; `T` is years. Delta is premium-point change per one
index point. Gamma is delta change per one index point. **Vega is per 1.00
absolute volatility** (divide by 100 for one vol-point). **Theta is per year**
(divide by 365 for a calendar-day presentation). **Rho is per 1.00 absolute
rate** (divide by 100 for one rate-point). Contract multiplier 100 is excluded
from every mathematical value. No GEX is calculated.

## Immutable input contract and provenance

`LocalGreeksInput`, `TemporalInput`, and `InputProvenance` are frozen records.
They require right, strike, expiration and replay timestamps, bid/ask, underlying,
rate, dividend, policies, source identifiers, event times, available times, rate
reference time, transformations, alignment/staleness state, and model version.
Every timestamp must be timezone-aware; naive time is `INVALID_INPUT`.

Successful output carries model and solver versions, calculation mode, replay
and expiration times, all three identifiers and relevant temporal fields,
bid/ask/MID, underlying/rate/dividend values and policies, time convention,
transformations, eligibility, and structured blocking reasons. These values are
sufficient to reproduce the calculation.

## Option-price and no-arbitrage policy

`MID_V1` selects `(bid + ask) / 2`. Missing/non-finite/negative sides and crossed
quotes are `INVALID_INPUT`. Zero bid, zero ask, and locked nonnegative markets are
handled explicitly by the same formula and are not silently rejected. With no
approved maximum spread, maximum age, or minimum premium, a caller identifying an
extreme spread or stale quote sets the policy unresolved and receives
`UNRESOLVED_POLICY`; this contract invents no threshold.

Before solving, the premium must lie in the European bounds:

* call: `max(0, S exp(-qT) - K exp(-rT)) <= C <= S exp(-qT)`;
* put: `max(0, K exp(-rT) - S exp(-qT)) <= P <= K exp(-rT)`.

A violation is malformed economic input (`INVALID_INPUT`). A premium inside
those broad bounds but outside prices reachable at the configured sigma bounds
is `NO_SOLUTION`; no IV attempt is disguised as a fallback.

## Underlying, rate, and dividend policies

Historical SPX remains `BLOCKED_UNRESOLVED`. Synthetic fixtures may supply an
exact-time underlying. A future real input must preserve price, source,
event/available time, staleness state, and versioned alignment policy. Nearest
future ticks, future interpolation, and backfill from future values are forbidden.
No real staleness threshold is selected here.

Rates preserve value, source, reference time, available/publication time, and
provenance. `LATEST_CAUSALLY_PUBLISHED_RATE` and `EXPLICIT_CAUSAL_RATE` are
designed options. `VERSIONED_APPROVED_FALLBACK` remains `UNRESOLVED_POLICY`.
In particular, SOFR for historical date D, published approximately 08:00 ET on
the following business day, cannot be treated as known intraday D merely because
it is retrievable later.

Dividend policies are `ZERO`, `EXPLICIT_ANNUAL_DIVIDEND`, and
`OTHER_VERSIONED_POLICY`; the last remains unresolved without an approved
version. `ZERO` is allowed for synthetic tests and is not asserted to be a final
economic SPX calibration.

## Time to expiration

`ACTUAL_SECONDS_OVER_365_DAYS_V1` computes exact UTC elapsed seconds from the
explicit valuation/replay timestamp to the explicit expiration timestamp and
divides by `365 * 24 * 60 * 60`. It preserves intraday precision and uses no
wall clock or exchange-calendar adjustment. Tests freeze 09:30, 12:00, 15:30,
15:45, exact expiration, and post-expiration behavior. Both `T == 0` and `T < 0`
fail closed as `INVALID_INPUT`.

## Solver and failure states

`LOCAL_SPX_IV_BISECTION_V1` uses sigma `[1e-8, 5.0]`, premium tolerance `1e-10`,
and at most 200 iterations. The midpoint and comparison order are fixed. Solver
exhaustion and an otherwise-valid price outside the sigma bracket return
`NO_SOLUTION`. The explicit statuses are `SOLVED`, `NO_SOLUTION`,
`INVALID_INPUT`, `NON_CAUSAL_INPUT`, and `UNRESOLVED_POLICY`. NaN/inf,
nonpositive spot/strike/T, invalid sigma-domain inputs, impossible premiums,
crossed/missing quotes, future availability, unresolved staleness, and exhaustion
fail closed; no NaN, infinity, negative IV, or arbitrary IV is returned.

## Causality gate

`greeks_reconstruction_eligibility` is pure and returns deterministic, sorted
reasons. Synthetic fixtures return `MATHEMATICAL_TEST_ONLY`, which never means
replay eligibility. Real replay returns `BLOCKED_NON_CAUSAL_INPUT` for any future
event/availability time, or `BLOCKED_UNRESOLVED_POLICY` for unresolved mappings
or policies. `ELIGIBLE_FOR_REPLAY` exists as a future contract state, but is
impossible on the current historical SPX route because its mapping is
`BLOCKED_UNRESOLVED`.

## Synthetic numerical validation

Versioned reference values in the tests were generated independently before this
implementation with the published Black–Scholes equations (normal CDF from an
independent high-precision calculator), not ThetaData. Fixtures cover ATM, ITM,
OTM, calls, puts, short T, low/high IV, nonzero rates and dividends. Tests also
check put–call parity, nonnegative Gamma/Vega, delta bounds, guaranteed price
monotonicity, and exact unit scaling.

IV round trips create synthetic premiums from known sigmas over both rights,
multiple strikes, maturities, rates, and volatilities, then demand deterministic
recovery. 0DTE tests cover T approaching zero, ATM/deep ITM/deep OTM, very low
and high premiums/volatility, locked quotes, zero bid/ask, and explicit
no-solution outcomes without overflow or non-finite results.

## Future ThetaData comparison protocol (not executed)

A later, separately authorized diagnostic may compare local IV, Delta, Gamma,
Vega, Theta, and Rho with ThetaData values calculated at request time. The record
must preserve local model version, all ThetaData request parameters, rate,
dividend, timestamps, underlying pairing, and option-price policy. Provider
output is diagnostic—not an absolute oracle—and final tolerances remain
unresolved. This phase makes zero provider calls.

## SpotGamma separation

Black–Scholes Gamma per contract is not Gamma Exposure, SpotGamma Gamma Index,
Zero Gamma, Call Wall, Put Wall, HIRO, or Volatility Trigger. No proprietary
metric is reconstructed and no local output uses a SpotGamma metric name.

## Remaining blockers and safety ledger

Provider Greeks/IV remain `EXCLUDED`; local Greeks/IV remain
`NEEDS_RECONSTRUCTION`; SPX, OI, trades, and quotes remain
`BLOCKED_UNRESOLVED`; cutover is `NO`. The nine human decisions are unchanged.
ThetaData calls, real datasets, TradeStation, runtime HTTP, OAuth, POST, orders,
DigitalOcean, backtests, loader/main execution, runtime modifications, and
mapping promotions are all zero.
