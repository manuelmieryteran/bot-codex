# Phase 5C-4A historical data contract

## Scope and boundary

The only supported flow is **already-loaded synthetic/provider-neutral rows →
`HistoricalDatasetAdapter` → `TemporalFirewall` → immutable
`HistoricalReplaySnapshot` → `replay_contract()` → 5C-3 temporal replay**.  This
phase has no loader, provider selection, network, credentials, order execution,
profit backtest, or runtime entry point.  Phase 4 and Phase 5 remain frozen.

## Field inventory

Categories: **A** market observation, **B** options observation, **C** derived at
tick, **D** prior state, **E** broker-synthetic, **F** configuration, **G**
unavailable historically, **H** not required by the current contract.  Frequency
is event-driven unless stated otherwise. `R` means required to reproduce the
relevant 5C-3 tick; `O` means optional/conditional. Missing required values make a
snapshot unusable; optional values stay absent (never silently filled).

|Category|Fields|Type / unit|Conceptual source; timestamp semantics; frequency|R/O, nullable; derivation|Look-ahead risk and missing treatment|
|---|---|---|---|---|---|
|A|`spot`, `es_price`|float / index points|market trade/quote; event and availability time; tick|R, no; raw|future quote/trade rejected; missing market makes snapshot unusable|
|A|`bid`, `ask`, `bid_size`, `ask_size`, `trade_price`, `trade_size`|float / currency; int / contracts|optionable instrument quote/trade feed; quote/trade event time; tick|R for current 5C-3 fixture, no; raw|quote/trade availability gated; no fill/interpolation|
|A|`bar_start`, `bar_end`, `bar_available_time`, `is_complete`|aware datetime, bool|bar builder/publication clock; per completed bar|O unless a bar is supplied; no|future/incomplete bars rejected|
|B|`call_oi`, `put_oi`, `oi_reference_date`, `oi_available_time`, `oi_source_semantics`|int / contracts; date, aware datetime, string|provider publication, not quote time; normally daily|R for current fixture, no|OI publication after replay rejected; missing OI cannot be inferred|
|B|option `bid`, `ask`, `trade_price`, `trade_size`|float / currency; int / contracts|observed option quote/trade; tick|R where option state is consumed, no|future quote/trade rejected|
|C|`gamma_balance`, `positive_dynamic_gex`, `negative_dynamic_gex`, `dealer_flow_gex`, `expected_move`, `vwap`, `iv`|float / ratio, currency exposure, points|calculation at tick; availability is max(input availability, compute time)|R for present laboratory, no; transformations must list input IDs/times|future close, settlement, volatility, interpolation, forward-fill, or window member rejected|
|C|`net_dynamic_gex`, `dealer_dynamic_gex`|float / currency exposure|sum of same-tick permitted GEX components|R at replay boundary, no|all components must have crossed firewall|
|C|`regime`, `flow_status`, `flow_usable`, `signal`, `streak`, `forced_exit`, entry/exit permission|enum/string, bool, int|deterministic decision logic at replay time|R, no; derived only from admitted inputs, prior state and config|future inputs rejected; missing dependency makes value unavailable|
|D|position state/contracts/entry side; pending order; execution and broker state|enum/string, int|previous accepted replay transition; known before current tick|R, no|future transition/fill rejected; absent state makes decision unusable|
|E|broker order status/state/event and synthetic fill/reject/cancel/unknown|enum/string|in-memory synthetic broker observation; event and actual availability time|O unless lifecycle transition occurs; no|future broker state/fill rejected; never fabricated|
|F|entry/forced-exit cutoffs, confirmation count, flow rules, `DRY_RUN`, execution flags/environment|time, int, bool, enum|versioned runtime/test configuration; effective-at time|R, no; not market data|wrong effective version is a provenance/configuration failure|
|G|provider-specific historical availability latency; official OI publication instant/semantics; historical quote corrections; locally computed Greek input lineage|provider metadata|not present in current synthetic dataset|unavailable, nullable until provider due diligence|must not be guessed; provider rows are unusable until demonstrated|
|H|credentials, account ID, P&amp;L, commissions, slippage model, real order IDs, cloud/deployment fields|not accepted|not needed for the current safety/decision contract|not required; prohibited or out of scope|must not enter fixtures or provenance|

Every raw observation additionally requires `identifier`, aware `event_time`,
aware `available_time`, aware `source_time`, monotonic unique
`ingestion_sequence`, `kind`, values, and provenance.  These metadata are not
decision values.  `source_time` is the timestamp stated by the source and may
differ from event or availability time.

No production staleness threshold was found in the current replay contract.
Accordingly, the adapter accepts no implicit threshold. A caller may supply a
clearly controlled threshold; tests use one labelled **TEST-ONLY** solely to
exercise classification.

## Structures and immutability

`HistoricalMarketObservation`, `HistoricalOptionsObservation`, and
`HistoricalBrokerObservation` contain raw observations only.
`HistoricalDerivedValue` contains a transformation plus paired input identifiers
and availability times. `HistoricalReplayInput` keeps those sets and prior state
separate. `HistoricalReplaySnapshot` is frozen and exposes immutable mappings;
it contains only admitted observations, derived values, prior state, quality,
and provenance.

## Temporal semantics and firewall

* **Event time**: when the represented event occurred.
* **Source time**: timestamp asserted by the source.
* **Available time**: earliest instant the algorithm could actually have read it.
* **Replay time**: simulated decision instant.

All timestamps must be timezone-aware. Market display semantics use
`America/New_York`; comparison remains correct after conversion to UTC, including
both DST folds. `available_time <= replay_time` is inclusive. One microsecond
later fails closed with `HistoricalLookaheadError`; it is never shifted, clipped,
or repaired.

Every observation and derived value crosses `TemporalFirewall`. It enforces
availability, OI publication time, bar completeness, chronological ordering,
unique sequence/identifier policy, provenance presence, and optional staleness
classification. A duplicate identical sequence/identifier is an explicit error;
a conflicting duplicate is also an explicit error and is never deduplicated.
Earlier `(event_time, ingestion_sequence)` after a later row is out of order.

For calculated IV/Greeks, each observed quote/trade, underlying price, rate,
time-to-expiry input, and any other model input must have its own identifier and
availability time. The derived availability cannot precede its inputs or compute
time. Current 5C-4A does not implement a pricing model.

## OI and bars

OI is never assumed contemporaneously known. An OI row requires
`oi_reference_date`, `oi_available_time`, and textual `oi_source_semantics`; both
row and OI availability must be at or before replay time.

A bar requires `bar_start`, `bar_end`, `bar_available_time`, and
`is_complete=True`. The convention is close-inclusive: a 09:30–09:35 bar may
cross at 09:35 only when its availability is also no later than 09:35; it cannot
cross at 09:32. VWAP/range windows explicitly list their inputs, all of which
must already be available. Future interpolation endpoints, forward-fill sources,
and window members fail closed.

## Provenance and quality

`Provenance` records source, source time, available time, transformation, and
input identifiers. It contains no credential or account identity. This lineage
answers why a value was known at a replay instant.

Quality states are `VALID`, `STALE`, `MISSING`, `OUT_OF_ORDER`, `FUTURE`,
`INCOMPLETE`, and `REJECTED`. Future, incomplete, ordering, and duplicate
violations raise and produce no partial snapshot. Missing required market data
or explicitly stale data produces an immutable unusable snapshot. Nothing
critical is filled silently.

Successful adaptation returns a deterministic `HistoricalAuditReport` with:
`rows_seen`, `rows_accepted`, `rows_rejected`, `future_rows_rejected`,
`duplicates`, `conflicting_duplicates`, `out_of_order`, `incomplete_bars`,
`missing_required`, `stale`, `snapshots_created`, and `unusable_snapshots`.
Fail-closed exceptions carry the partial report as `audit_report`, while never
returning a partial snapshot.

Example for three valid synthetic rows:

```text
rows_seen=3 rows_accepted=3 rows_rejected=0 future_rows_rejected=0
duplicates=0 conflicting_duplicates=0 out_of_order=0 incomplete_bars=0
missing_required=0 stale=0 snapshots_created=1 unusable_snapshots=0
```

## Synthetic coverage and safety ledger

Fixtures cover ordered/out-of-order ticks, identical/conflicting duplicates,
missing/stale values, future observations, incomplete bars, delayed OI,
quote/trade timing, future broker fills, calculated inputs, interpolation,
forward-fill, future window members, exact boundaries, and both DST transitions.
They are synthetic and auditable; no real dataset is included.

The required external-activity ledger remains zero for TradeStation, real
ThetaData, SpotGamma, QuantConnect, HTTP, OAuth, POST, orders, DigitalOcean,
access-token reads, and `main()` executions. Cutover remains **NO**.

## Open questions for 5C-4B

1. Which provider exposes original publication/receipt time rather than only
   exchange event time, including corrections?
2. What are the documented publication instant, reference date, revision policy,
   and historical reproducibility guarantees for OI?
3. Are quote/trade sequences stable and unique, and how are cancellations and
   corrections represented?
4. Are 5-minute bars supplied or locally aggregated, and what exact close and
   dissemination convention applies?
5. Can every IV/Greek input and model version be reconstructed without a future
   settlement, close, rate, or volatility surface?
6. What contractual staleness limits, if any, should apply per observation kind?

**Exact 5C-4B recommendation:** perform provider due diligence against these six
questions, write a loader-independent mapping specification and synthetic
conformance fixtures first, and do not ingest a real row until event/source/
availability semantics—especially OI and corrections—are evidenced and tested.
