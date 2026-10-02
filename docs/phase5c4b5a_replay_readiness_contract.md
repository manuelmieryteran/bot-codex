# FASE 5C-4B.5A — Causal historical replay readiness gap contract

## Scope and answer

A historical SPX 0DTE session is **not** currently
`CAUSALLY_REPLAY_ELIGIBLE`. It can receive that designation only when every raw
and derived input required by the requested feature configuration independently
has proven point-in-time availability, source-specific correction and
missingness semantics, approved staleness/alignment policies, sufficient
account-verified depth, complete versioned provenance, and deterministic
validation. Acquisition success alone is never sufficient.

This phase is offline evidence analysis. It made zero provider calls, read no
credentials, downloaded no datasets, built no loader or backtest, changed no
runtime mapping, and performed no cutover. The canonical machine-readable
contract is
[`phase5c4b5a_replay_readiness.json`](evidence/phase5c4b5a_replay_readiness.json).
It freezes `mapping_promotions=0` and `cutover=NO`.

## Four independent layers

1. **L1 provider capability** describes what the provider says exists.
2. **L2 account acquisition** records what this account actually returned.
3. **L3 causal input eligibility** proves what was available by `replay_time`.
4. **L4 replay readiness** requires the complete requested bundle.

No L1→L2, L2→L3, or partial-L3→L4 promotion is automatic. All promotion gates
set `automatic_promotion_allowed=false`.

## Frozen evidence and mapping

The persisted 4C-2C evidence records exactly seven `VERIFIED_AVAILABLE`
capabilities: account metadata, SPX/SPXW contract list, option quotes, open
interest, IV/first-order Greeks, EOD Gamma, and interest-rate history. Trades
remain `AMBIGUOUS/EMPTY_SUCCESS`; SPX index history remains
`ERROR/TRANSPORT_ERROR/UNRESOLVED`; all account depth is
`2026-01-15/SINGLE_DATE_ONLY`; account tier is `NOT_PERSISTED/UNRESOLVED`.
P2 remains an `ACQUISITION_SCOPE_ANOMALY` with 17,326 rows.

The frozen mapping remains: provider historical Greeks/IV `EXCLUDED`; local
Greeks/IV `NEEDS_RECONSTRUCTION`; SPX, OI, trades, and quotes
`BLOCKED_UNRESOLVED`; historical SPXW 0DTE universe
`READY_WITH_CONSERVATIVE_RULE/LOW`. Nothing in 5A promotes these values.

## Source-specific findings

### Universe and contract metadata

The conservative universe is root `SPXW`, expiration date D, and observed
trade/quote activity on D. By itself this permits a deliberately incomplete
conservative universe, but it must fail closed for incomplete identity,
unknown expiration time/settlement, holidays, special expirations, or ambiguous
SPX/SPXW classification. Raising confidence requires versioned historical
listing/delisting and calendar/settlement metadata, including inactive listed
contracts. Residual survivorship remains explicit.

Required metadata is root, expiration, expiration time, strike, right,
settlement style, stable contract identity, reference time, available time and
provenance. Expiration date=D is derivable for the selected 0DTE rule;
expiration/right/strike/symbol were observed. Expiration time, settlement,
historical availability, and special-calendar behavior are unresolved.

### Quotes

P3 proves acquisition for one date/contract, not causal use. Event timestamp is
known, but receipt/client `available_time`, sequence, a maximum latency bound,
correction behavior, zero bid/ask semantics, approved quote age, and approved
cross-feed skew are absent. OPRA NBBO does not fill those gaps. A future minimum
gate needs point-in-time availability evidence (or an explicitly approved,
defensible conservative bound), correction/condition and zero-value rules, a
versioned last-causally-available selector, and adversarial tests. Future
interpolation and backfill remain prohibited; no rule is approved here.

### Trades

Two independent blockers remain. L2 is ambiguous because P4 was an empty
success. L3 remains blocked even after any future acquisition proof: exchange
time plus a signed 32-bit wrapping, non-global sequence cannot establish
received-by-T ordering; late/cancel/correction codes do not link cancellation to
the original.

Trades are `NOT_REQUIRED` for quote-based IV, `REQUIRED` for dealer-flow,
aggressor classification and dynamic GEX, and `OPTIONAL` for generic signal
reconstruction (the requested signal configuration determines whether the
trade-dependent branch is enabled). This does not change strategy behavior.

### Open interest

Value, event time, available time, correction policy and missingness are
separate. The value denotes previous-trading-day OI and the record has an OPRA
daily-message timestamp. Neither proves client availability; there is no
pre-09:30 SLA. Multiple messages may occur without a correction flag, and an
absent message is not reported zero. A future selector must use only an approved
as-of rule, distinguish `ZERO`, `NO_MESSAGE`, `MISSING`, and `UNKNOWN`, and must
not presume 06:30 ET availability.

### SPX underlying

P8 proves only a transport error; it proves neither denial nor availability.
Account acquisition, account-specific depth, client availability, cross-feed
alignment, gap/missingness and maximum age are independent blockers. The feed
is separate from OPRA, has no shared sequence, may omit ticks when unchanged,
and supplies no coverage flag. There is no approved ES, SPY, TradeStation, or
provider-Greeks fallback.

### Rate and dividend

Rate acquisition exists and the causal contract represents publication time,
but same-date SOFR published D+1 is unavailable intraday D. A human must
version and approve either the latest causally published rate, a fixed rate, or
another explicit compatible policy; 5A chooses none.

`LOCAL_SPX_BS_V1` requires an explicit dividend yield. `ZERO` is only a
mathematical/test policy until human approval; approving it in a later phase
would require versioned provenance and explicit acceptance of pricing/Greek
model error from omitted dividends. It is not approved here.

### Corrections, missingness, staleness and alignment

Correction contracts remain source-specific: quote behavior is unknown; trade
condition codes exist but records are unlinked; OI allows multiple messages
without a flag; SPX behavior is unknown. A common overwrite rule would be
invalid.

`MISSING`, reported `ZERO`, `NO_MESSAGE`, and `UNKNOWN` remain distinct. Silent
forward-fill and zero imputation are prohibited. No max quote age, max SPX age,
or max cross-feed skew exists. Future thresholds require empirical update
cadence, latency, outage and session-regime coverage plus explicit approval;
5A invents no number.

Alignment must compare OPRA and Cboe event times and their independently proven
available times. `LAST_CAUSALLY_AVAILABLE` is representable; `EXACT_SYNTHETIC`
is test-only. `NEAREST_FUTURE`, `FUTURE_INTERPOLATION`, and `FUTURE_BACKFILL`
are prohibited. A real policy needs evidence for both timelines and a human
approved event-time and availability-time skew boundary.

### Calendar and depth

A future calendar/metadata implementation must version `America/New_York`, DST,
trading date/open, date=D expiration, expiration time, holidays, early closes,
AM/PM settlement, SPX versus SPXW, and historical changes in expiration
availability. Unknown holidays or special listings fail closed.

Only 2026-01-15 is account verified. Provider-described history never proves
account depth. The JSON depth matrix therefore uses
`required_backtest_depth=HUMAN_DECISION_PENDING` and
`BLOCKED_HISTORICAL_DEPTH` for every dataset.

## Local IV and Greeks prerequisite gate

The mathematical implementations `LOCAL_SPX_BS_V1`,
`LOCAL_SPX_IV_BISECTION_V1`, `MID_V1`, and
`ACTUAL_SECONDS_OVER_365_DAYS_V1` remain mathematical/test-only. Promotion to
`ELIGIBLE_FOR_REPLAY` requires causal quote and underlying, causal selected
rate, approved dividend, causal contract metadata, approved staleness and
alignment, full provenance, frozen model/transformation versions,
deterministic repeatability, and real-input contract/failure validation.
Provider-computed historical Greeks/IV remain excluded.

## Feature matrix, DAG and technical priority

The JSON `feature_requirements` matrix covers SPX spot, walls, Gamma Flip,
static/dynamic GEX, dealer flow, Dealer Dynamic GEX, Gamma Balance/Regime,
signals, risk gate and entry permission. It explicitly records raw/derived
inputs and whether trades, local Greeks, SPX, OI and quotes are mandatory.

The `dependencies` and deterministic `topological_order` form the resolution
DAG. Technical priorities derive from graph position: unavailable primitive
facts/policies are foundational; causal selectors are upstream; reconstruction,
depth and session gates are downstream. Trade-only branches are optional
unless the requested feature selects them. These labels are not business
scores.

## Pure session gate and provenance

`evaluate_session_replay_readiness(required_inputs, eligibility)` performs no
I/O. Empty or unknown requirements return `INVALID`; known required inputs
produce every blocker; `READY` occurs only when all are `RESOLVED` or explicitly
`RESOLVED_WITH_CONSERVATIVE_RULE`. The function never promotes acquisition.

Every future input must preserve provider, dataset, contract identity,
`event_time`, `available_time`, source/reference time, retrieval context, and
policy, mapping, model and transformation versions.

## Next minimum phase (recommendation only)

The next minimum technical phase is an **offline human policy/evidence
specification** for point-in-time availability, source-specific corrections,
missingness, staleness/skew, calendar/metadata, and required historical depth.
It should define auditable decisions and fixtures before any separately
authorized acquisition, loader, mapping promotion, or backtest. This phase does
not execute that recommendation.
