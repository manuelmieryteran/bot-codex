# Phase 5C-4B — provider due diligence and mapping specification

**Specification:** `5C-4B.1` · **consulted:** 2026-10-01 · **scope:** public
documentation only. No dataset or authenticated endpoint was queried. `DOCUMENTED`
means that the linked text explicitly supports the narrow claim; it does not imply
point-in-time suitability. Anything not established below remains `UNKNOWN`.

## Safety boundary and method

This is research and a declarative contract, not an ingestion design. There is no
loader, transport, credential lookup, provider call, backtest, P&L, runtime edit,
or cutover. Public documentation was read using unauthenticated GET and public Git
repositories. Calls to ThetaData, TradeStation, QuantConnect and SpotGamma APIs,
OAuth, POST, orders, DigitalOcean, `TS_ACCESS_TOKEN` reads and `main()` executions
were all **zero**. Raw future data is immutable; normalized data and replay
snapshots are separately versioned derivatives and must never overwrite raw.

## Evidence ledger

|ID|Provider|Claim (and boundary)|Official source/document|Class|Confidence|Unresolved ambiguity|
|---|---|---|---|---|---|---|
|T1|ThetaData|Historical option quote schema exposes millisecond-of-day, bid/ask prices, sizes, exchanges and conditions; pagination uses `next_page`.|[Historical option quote](https://docs.thetadata.us/operations/get-hist-option-quote.html), [pagination](https://docs.thetadata.us/Articles/Performance-And-Tuning/Pagination.html)|DOCUMENTED|high|No receipt/availability clock, stable ordering, duplicate or correction guarantee is stated.|
|T2|ThetaData|Historical option trades expose `ms_of_day`, sequence, conditions, size, exchange, price and records-back.|[Historical option trades](https://docs.thetadata.us/operations/get-hist-option-trade.html)|DOCUMENTED|high|Meaning/stability of sequence, late reports, cancels, corrections and download revision are not established.|
|T3|ThetaData|Option OI is reported by OPRA around 06:30 ET and represents previous trading-day end; a zero-interest contract may receive no new message.|[Historical option open interest](https://docs.thetadata.us/operations/hist-option-open_interest.html)|DOCUMENTED|high|“Approximately” is not an exact availability timestamp; timezone label/DST, revision and point-in-time history are not guaranteed.|
|T4|ThetaData|Historical Greeks/IV endpoints exist; trade Greeks associate last underlying price at option trade time and can expose option and underlying millisecond fields.|[Trade Greeks](https://docs.thetadata.us/operations/get-hist-option-trade_greeks.html)|DOCUMENTED|high|Whether stored results can later be recalculated/revised is unknown.|
|T5|ThetaData|Greeks use Black-Scholes, per-tick underlying, bisection IV, ignore dividends unless overridden, and default to latest supplied SOFR (reported one day later).|[Option Greeks methodology](https://docs.thetadata.us/Articles/Data-And-Requests/Option-Greeks.html)|DOCUMENTED|high|Expiry clock/day-count details, index treatment, historical model version and causal SOFR selection are incomplete.|
|T6|ThetaData|The public endpoint labels show Standard/Pro entitlement distinctions.|Endpoint pages above|DOCUMENTED|medium|The repository contains no evidence of **our** subscribed plan; actual entitlement is UNKNOWN.|
|T7|ThetaData|Index historical EOD/OHLC/price endpoint families are documented.|[Historical index price](https://docs.thetadata.us/operations/get-hist-index-price.html)|DOCUMENTED|medium|SPX entitlement, history depth, dissemination latency and causal synchronization with OPRA are unconfirmed.|
|C1|Cboe|SPX options use a $100 multiplier; standard SPX is AM-settled and SPXW is PM-settled, with product-specific hours.|[Cboe SPX specifications](https://www.cboe.com/tradable_products/sp_500/spx_options/specifications/)|DOCUMENTED|high|Exchange contract semantics do not establish ThetaData storage or availability.|
|C2|Cboe|Weeklys include daily SPX expirations subject to exchange calendar/product rules.|[Cboe SPX options](https://www.cboe.com/tradable_products/sp_500/spx_options/)|DOCUMENTED|high|Historical listing calendar still needs versioned metadata.|
|Q1|QuantConnect|LEAN supports Index, Future, IndexOption data and history requests with tick/quote/trade/open-interest data types where datasets provide them.|[LEAN securities](https://www.quantconnect.com/docs/v2/writing-algorithms/securities/key-concepts), [history](https://www.quantconnect.com/docs/v2/writing-algorithms/historical-data/history-requests)|DOCUMENTED|medium|Dataset-, symbol-, date-, resolution- and plan-specific availability is not thereby proven.|
|Q2|QuantConnect|Dataset listings define separate licensing/pricing and availability properties.|[Data Market](https://www.quantconnect.com/datasets/)|DOCUMENTED|medium|No purchase/activation was performed; SPXW microstructure sufficiency remains UNKNOWN.|
|S1|SpotGamma|Call Wall, Put Wall, Gamma Flip/Zero Gamma, Gamma Index, HIRO and Volatility Trigger are vendor-defined analytics.|[SpotGamma glossary](https://support.spotgamma.com/hc/en-us/categories/1500000758601-Glossary), [HIRO](https://spotgamma.com/hiro/)|DOCUMENTED|medium|Public material does not publish complete versioned formulas/inputs sufficient for equivalent reconstruction.|
|TS1|TradeStation|Market-data endpoints include historical bars and brokerage endpoints include orders/historical orders as distinct authenticated resources.|[Official API specification](https://api.tradestation.com/docs/specification/)|DOCUMENTED|high|Bars are not tick microstructure; historical broker-state event availability and retention are not established.|

The ThetaData pages were also cross-checked against the public documentation
snapshot repository; because that mirror is not provider-controlled it is
corroboration, not a higher evidence class. No claim above relies on Cboe to
answer a ThetaData-specific question.

## ThetaData capability inventory

|Data / conceptual endpoint|Historical/live; resolution|Timestamp / zone|Entitlement / depth|Corrections, order, limitations|
|---|---|---|---|---|
|Index price (`hist/index/price`, OHLC/EOD)|historical endpoint family; tick/bar/EOD varies|`ms_of_day` + date, docs describe EST encoding|endpoint-dependent; our plan and depth UNKNOWN|availability clock and SPX/OPRA synchronization UNKNOWN|
|Option contracts/list metadata|historical list dates/contracts and roots/expirations/strikes|contract date fields; no receipt time|plan/depth UNKNOWN|use for expiration/strike/right only after calendar/version capture|
|Option trades|tick history; price, size, exchange, conditions, sequence|milliseconds from midnight “EST” + date|page labeled by tier; actual entitlement/depth UNKNOWN|sequence exists, but semantics/order/cancels/corrections/late reports/duplicates UNKNOWN|
|Option quotes|tick history; bid/ask, sizes, exchange, condition|milliseconds from midnight “EST” + date|actual entitlement/depth UNKNOWN|OPRA/NBBO construction and locked/crossed handling not sufficiently documented for causal certification|
|Open interest|one OPRA report, normally daily|row time near 06:30 ET; date; prior-day-end value|Standard/Pro label; depth/our entitlement UNKNOWN|missing zero update possible; exact publication, revision, correction history UNKNOWN|
|IV/Greeks|historical tick endpoints and trade-associated variants|option tick plus underlying time on trade endpoint|Pro labels on relevant endpoints; our access UNKNOWN|provider-calculated; model/version/recalculation policy incomplete|
|Pagination|response pages following `next_page`|not an event clock|terminal config-dependent|pages can expire and IDs need not be consecutive; no global sort guarantee documented|

### OI conclusion (critical)

Classification: **UNSAFE_WITHOUT_EXTERNAL_EVIDENCE**. T3 identifies a prior-day
close measure delivered at approximately 06:30 ET. That supports, at most, a
future conservative candidate rule (“not before a verified per-row publication
clock, and never assign absent updates as zero”). It does **not** identify the
exact instant known on each historical day, a revision log, or whether today's
historical response is point-in-time. Consequently OI at 09:30/10:00 cannot yet
be certified and the executable declaration remains `BLOCKED_UNRESOLVED`.

### Trades and quotes conclusion

The documented schemas are useful and millisecond-resolution event fields,
conditions, sizes and (trades) a sequence are available. They do not document a
provider receipt/availability timestamp or sufficient guarantees for ordering,
duplicates, late reports, cancel/correct processing, stable sequences, or
point-in-time revisions. Quote rows expose bid/ask conditions but the reviewed
material does not prove that every row is a causally reproduced NBBO. Both
feeds therefore remain **NEEDS_PROVIDER_CONFIRMATION**, not READY.

### IV and Greeks conclusion

Provider IV and delta/theta/vega/rho/epsilon/lambda plus second/third-order
families (including gamma endpoints) are distinct from local Greeks. T4–T5
establish the broad calculation method but not our entitlement, exact expiry
convention, model-version history or non-recalculation guarantee. Provider
values are blocked. A local value is `RECONSTRUCT` only if the contemporaneous
option price/quote, underlying, rate known then, dividends, expiration clock,
contract metadata, model/version and every input's availability cross the
firewall; it must be labelled local and never “ThetaData” or “SpotGamma”.

### SPX and ES underlying conclusion

ThetaData documents index endpoint families, but causal SPX receipt time and
synchronization with each option row remain unknown. No reviewed ThetaData
material establishes ES. QuantConnect or TradeStation futures history is a
possible alternate only after dataset/contract mapping and availability are
confirmed. Equal printed timestamps across sources are never treated as
simultaneous availability.

## Secondary-provider assessments

### SpotGamma classification

|Metric|Class|Reason|
|---|---|---|
|Call Wall; Put Wall|B — APPROXIMATELY_RECONSTRUCTIBLE|A separately named local OI/gamma concentration level may be built, but equivalence to the proprietary selection logic is unproven.|
|Zero Gamma / Gamma Flip|B — APPROXIMATELY_RECONSTRUCTIBLE|A model-specific local zero crossing is possible only with causal inputs; it is not the vendor metric.|
|Gamma Index|C — PROPRIETARY / NOT REPRODUCIBLE|Complete formula/version lineage is not documented.|
|HIRO|D — REQUIRES HISTORICAL SPOTGAMMA DATA|Vendor real-time flow analytic cannot be recreated equivalently from the currently mapped raw fields.|
|Volatility Trigger|C — PROPRIETARY / NOT REPRODUCIBLE|Public description is insufficient for equivalent historical calculation.|
|Absolute Gamma / Key Gamma Strike|B — APPROXIMATELY_RECONSTRUCTIBLE|Only explicitly labelled local analogues may be produced.|

### QuantConnect

QuantConnect is potentially useful for research/backtest access to SPX/index,
ES futures, SPY, and option datasets, with resolution determined by each dataset
and license. Generic LEAN support is not proof that SPX/SPXW quotes, trades, OI,
Greeks, required depth, corrections, and availability clocks coexist for our
dates. Thus **DATA AVAILABLE FOR RESEARCH/BACKTEST** may become true after a
catalog/plan check, while **SUFFICIENT FOR CURRENT MICROSTRUCTURE CONTRACT** is
not demonstrated. No paid capability is assumed or activated.

### TradeStation

TradeStation's authenticated market-data history (notably bars) is distinct from
brokerage order/history resources. It may later complement SPX/ES bar research
or broker-state reconciliation, but public specification review does not prove
point-in-time tick availability, event-sourced historical order states, or
retention sufficient for this replay. OAuth was not used. Broker rows remain
excluded from provider ingestion in this phase.

## Mapping matrix against 5C-4A

`event/source/available` columns mean a documented field, not an invented time.
Depth and entitlement are UNKNOWN unless a future account-neutral document
proves them.

|Field(s)|Required|Preferred / alternate|Provider field|Event?|Available?|Source?|Corrections?|Depth / entitlement|Risk|Status / notes|
|---|---:|---|---|:---:|:---:|:---:|:---:|---|---|---|
|spot|yes|ThetaData / QC|index price time/value|yes|no|yes|no|UNKNOWN|cross-feed latency|NEEDS_PROVIDER_CONFIRMATION|
|es_price|yes|QC or TS / none|future trade/bar|yes|no|yes|no|UNKNOWN|contract roll + latency|NEEDS_PROVIDER_CONFIRMATION|
|bid, ask, bid_size, ask_size|yes|ThetaData / QC|quote fields|yes|no|yes|no|UNKNOWN|receipt/NBBO/revisions|NEEDS_PROVIDER_CONFIRMATION|
|trade_price, trade_size|yes|ThetaData / QC|trade price/size|yes|no|yes|no|UNKNOWN|late/corrected events|NEEDS_PROVIDER_CONFIRMATION|
|expiration, strike, right|conditional|ThetaData / Cboe metadata|contract object|date/meta|no|yes|no|UNKNOWN|historical listings|NEEDS_PROVIDER_CONFIRMATION|
|OI + reference/available/semantics|yes|ThetaData / QC|open_interest/date/ms_of_day|partial|approximate|yes|no|UNKNOWN|critical lookahead|NEEDS_PROVIDER_CONFIRMATION|
|IV, delta, gamma, other Greeks|yes|local; ThetaData candidate / none|Greek endpoint fields|yes|no|partial|no|UNKNOWN|recalculation/model inputs|NEEDS_RECONSTRUCTION|
|bars + completeness|conditional|local / provider|OHLC fields + local lineage|yes|local only|yes|UNKNOWN|UNKNOWN|incomplete bar|READY_WITH_CONSERVATIVE_RULE only for locally sealed bars|
|GEX/expected_move/VWAP/regime/flow/signal|yes|local / none|none|derived|derived|lineage|required immutable inputs|n/a|future inputs|NEEDS_RECONSTRUCTION|
|prior state/config|yes|versioned local / none|snapshot/config|yes|yes|yes|POINT_IN_TIME|local|wrong version|READY when hash/effective time captured|
|broker state|conditional|TradeStation / synthetic|order resources|partial|no|partial|no|UNKNOWN|broker revisions|EXCLUDE provider data; synthetic only|
|credentials/P&L/cloud|no|none|none|no|no|no|n/a|n/a|prohibited|EXCLUDE|

## `available_time` and correction policies

|Type|Proposed available time|Class|Correction class / replay rule|
|---|---|---|---|
|Theta index/trade/quote|No proposal: require captured receipt/publication evidence|UNRESOLVED|UNKNOWN; reject|
|Theta OI|Per-row verified publication; never earlier than documented approximate 06:30 ET|CONSERVATIVE_ASSUMPTION|UNKNOWN; still reject until exact rule and revisions confirmed|
|Provider Greeks/IV|Maximum availability of option row, underlying and all model inputs plus computation|UNRESOLVED|UNKNOWN; reject provider value|
|Locally completed bar|Local seal clock >= bar end and all constituent availability times|CONSERVATIVE_ASSUMPTION|POINT_IN_TIME if immutable inputs/versioned builder; conditional eligibility|
|Local derived value|Maximum input availability and compute time|DOCUMENTED_PROVIDER_TIME (contract-enforced lineage, not a market-provider assertion)|POINT_IN_TIME if inputs are PIT; reconstruct|
|Prior replay state/config|Committed transition/effective-at time|DOCUMENTED_PROVIDER_TIME (local record)|POINT_IN_TIME; eligible with hash/version|
|Broker history|No proposal|UNRESOLVED|UNKNOWN; excluded|

`POINT_IN_TIME` means the exact record as observable then is preserved.
`LATEST_REVISED` means the current corrected value may differ and is blocked.
`UNKNOWN` is equally blocked. A correction may only be represented as a new,
ordered immutable event retaining the superseded raw record; it must never
silently replace raw. Critical `UNRESOLVED` rows must be rejected before
`TemporalFirewall`, whose existing required concrete timestamp must not be
filled with a guessed value.

## Dataset manifest and storage lifecycle

Every future immutable raw object must have: `provider`, `dataset_type`,
`symbol`, `date_range`, `downloaded_at`, `provider_version`, `schema_version`,
`query_parameters`, `raw_file_hash`, `adapter_version`,
`mapping_spec_version`, `timezone`, and `notes`. Query parameters must be
canonicalized and secrets excluded. Lifecycle is **RAW (immutable bytes) →
NORMALIZED (derived, content-addressed) → REPLAY SNAPSHOT (derived, references
inputs)**. New provider revisions create new raw objects/manifests.

## Eligibility gate, conformance, and GO/NO-GO

`historical_replay_eligibility()` is pure and precedence is fail-closed:
EXCLUDE/UNAVAILABLE → `EXCLUDED`; reconstruction → `RECONSTRUCT`; provider
confirmation, unresolved availability, or non-PIT corrections →
`BLOCKED_UNRESOLVED`; conservative evidenced rule →
`ELIGIBLE_WITH_CONSERVATIVE_RULE`; otherwise `ELIGIBLE`. Synthetic tests cover
explicit/missing availability, delayed OI, revised/PIT/unknown correction rows,
quote/trade sequence, and locally reconstructed Greek.

|DATA TYPE|STATUS|EVIDENCE|REPLAY RULE|
|---|---|---|---|
|SPX price|NO-GO|T7 incomplete|block pending availability/revisions|
|ES price|NO-GO|Q1/TS1 generic only|block pending contract/tick evidence|
|option trade|NO-GO|T2 schema only|block pending receipt/corrections/order|
|option quote; bid/ask sizes|NO-GO|T1 schema only|block pending receipt/NBBO/corrections|
|OI|NO-GO|T3 prior-day/approx. publication|fail closed; no intraday replay yet|
|IV; Delta; Gamma; other Greeks|RECONSTRUCT/NO-GO provider|T4–T5 incomplete lineage|local only after every causal input; provider blocked|
|Call Wall; Put Wall; Zero Gamma|ANALOGUE ONLY|S1 incomplete formula|label local, never SpotGamma-equivalent|
|HIRO|NO-GO|S1 proprietary feed|requires historical SpotGamma data|
|Volatility Trigger|NO-GO|S1 incomplete formula|exclude equivalent reconstruction|
|broker order state|NO-GO|TS1 resource only|synthetic only; provider excluded|

## Unresolved questions and explicit exclusions

Provider confirmation is required for: exact event versus SIP/provider receipt
clocks and timezone/DST; stable total ordering/sequence uniqueness; late,
duplicate, cancel/correct records; historical response revision policy; exact OI
publication per date and absent-message semantics; index/option synchronization;
SPX/SPXW symbols and historical listings; plan and depth; Greek model version,
expiration/day count, rate/dividend/index inputs and recalculation; and QC/TS
symbol-, resolution-, license- and retention-specific coverage.

Excluded in 5C-4B: real rows/datasets, endpoint trials, credentials, paid plan
changes, loaders/storage, runtime integration, broker imports, proprietary-name
substitution, backtests, strategy/performance statistics, optimization, orders,
deployment and cutover. **Exact next step:** send the unresolved questions to
ThetaData support without credentials or data calls, obtain written plan-specific
answers and sample schemas, version that evidence, then extend synthetic
conformance tests. Do not ingest even one real row until OI, availability and
correction gates are resolved.
