# Phase 5C-4B.1 — ThetaData provider-confirmation package

**Status:** evidence collection only · **provider contact:** not yet authorized ·
**mapping changes:** none · **real-data ingestion:** none

## Minimal context and response format

We are assessing whether historical SPX option data can support a causal,
point-in-time research replay. We must distinguish when an event occurred
(`event_time`) from when it was observable by a ThetaData client
(`available_time`). We are not asking ThetaData to review our software or
strategy, and no credentials, account identifier, positions, or proprietary
signals are part of this request.

Please answer each numbered question independently. For historical records
downloaded today, use one of these classifications where requested:
`POINT_IN_TIME` (the record observable then is preserved), `LATEST_REVISED`
(only today's revised record is returned), `MIXED` (identify the cases), or
`UNKNOWN`. Exact endpoint/schema documentation, a written support statement,
and redacted sample response/message pairs are acceptable evidence. A marketing
description without field semantics is not sufficient.

Priorities are: **P0** blocks every real replay; **P1** blocks one data
category; **P2** affects fidelity; **P3** is informative.

### How acceptance outcomes will be evaluated

These criteria describe a future human decision; they do **not** change the
current mapping.

* **READY (R):** authoritative evidence establishes an exact causal field/rule,
  point-in-time corrections, scope, timezone, and stable semantics for the
  affected field.
* **READY_WITH_CONSERVATIVE_RULE (C):** authoritative evidence gives a safe
  upper availability bound or restricted subset, but not an exact observation
  instant; replay can delay or restrict the field without guessing.
* **NEEDS_RECONSTRUCTION (N):** evidence says the provider value/stream is not
  preserved as observed, but identifies complete, causally timestamped raw
  inputs from which a separately labelled local value can be rebuilt.
* **EXCLUDED (X):** evidence says the capability is unavailable, cannot be
  reconstructed causally, has only latest-revised/unknown critical semantics,
  or is outside the entitled product.

In every row below, `R/C/N/X` specializes those four outcomes. Silence,
ambiguity, an unsupported inference, or `UNKNOWN` leaves the mapping
`BLOCKED_UNRESOLVED`; it is not an acceptance outcome.

## Questions for ThetaData support

### Point-in-time and revision policy

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|PIT-01 · P0|Option trades|Does a historical option-trade record downloaded today represent exactly the message a client could have received then, or the currently stored result after later correction/reprocessing? Classify it as `POINT_IN_TIME`, `LATEST_REVISED`, `MIXED`, or `UNKNOWN`; for `MIXED`, identify the boundary.|Prevents revised trades from appearing before they were known.|Endpoint/version policy plus correction example.|R: PIT message history and availability are preserved / C: a documented PIT subset or safe cutoff exists / N: original messages and corrections can be rebuilt from causal raw fields / X: latest-only or irreducibly unknown.|
|PIT-02 · P0|Option quotes|Same question and classification for historical option quotes.|A current corrected quote is not necessarily the quote observable at replay time.|Version policy plus original/corrected quote example.|R: PIT quote messages preserved / C: documented PIT subset or delayed bound / N: causal quote stream can be rebuilt / X: latest-only or unknown.|
|PIT-03 · P0|Open interest|Same question and classification for historical open interest.|Later OI correction creates direct look-ahead.|OI publication/revision policy and dated example.|R: every publication/revision is PIT / C: immutable value after a documented safe cutoff / N: publications can be rebuilt from causal messages / X: latest-only or unknown.|
|PIT-04 · P1|Index data|Same question and classification for historical index data, including SPX prints.|A revised index print may contaminate option replay.|Index revision policy and corrected-print example.|R: PIT prints preserved / C: certified immutable subset or safe delay / N: PIT prints reconstructible from exposed causal messages / X: latest-only or unknown.|
|PIT-05 · P1|Greeks|Same question and classification for each available historical Greek, including Gamma.|A value recalculated under a newer model is not historically observable output.|Greek storage/recalculation and model-version policy.|R: displayed PIT values/version retained / C: fixed documented subset/version / N: complete PIT inputs support local reconstruction / X: otherwise.|
|PIT-06 · P1|Implied volatility|Same question and classification for historical implied volatility.|Later recalculation can leak revised inputs or methodology.|IV storage/recalculation and model-version policy.|R: displayed PIT IV retained / C: fixed documented subset/version / N: complete PIT inputs support local reconstruction / X: otherwise.|

### Open interest — highest-priority category

The public documentation already indicates that OPRA OI is normally reported
around 06:30 ET, represents the prior trading-day end, and may have no new
message for a zero-OI contract. The questions below seek only the unresolved
precision, exception, and revision semantics.

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|OI-01 · P0|OI meaning|Precisely what does a historical `open_interest` value represent, including its source message and reference session?|Defines the economic observation without inferring semantics.|Field specification or written support definition.|R: exact source/reference semantics / C: safe documented restricted interpretation / N: semantics support rebuilding a local measure / X: ambiguous or unsuitable.|
|OI-02 · P0|OI reference date|For trading date D, is the returned value calculated at close D-1, close D, or another reference? How is the row date assigned around weekends and holidays?|Prevents a future close from entering session D.|Calendar-aware specification with an example spanning a non-trading day.|R: deterministic reference-date rule / C: conservative calendar rule / N: source messages permit reconstruction / X: no reliable association.|
|OI-03 · P0|OI publication time|Is an exact historical timestamp retained for when each OI value became available to ThetaData clients, rather than the approximate 06:30 ET convention? Identify field, precision, and timezone/DST semantics.|The replay needs per-day `available_time`.|Schema and dated row/message example.|R: exact client-availability timestamp / C: guaranteed later bound / N: timestamp derivable from retained causal messages / X: neither exists.|
|OI-04 · P0|OI pre-open guarantee|If no exact timestamp exists, can ThetaData guarantee that session-D OI was available to **all** clients before 09:30 ET? State timezone, exceptions, affected dates/products, and the latest guaranteed time.|A universal bound could support a conservative pre-open rule.|Written SLA/specification defining scope and exceptions.|R: exact universal bound / C: conservative guaranteed bound/subset / N: auditable logs reconstruct availability / X: no guarantee.|
|OI-05 · P1|Late/missing OI|What is returned or disseminated when OPRA supplies OI late or initially supplies no value? How can late delivery be distinguished from a true zero or unchanged/no-message state?|Missing must never be silently treated as zero.|Message-state schema and late/missing example.|R: explicit causally timed states / C: rule that excludes ambiguous rows / N: states reconstructible from messages / X: indistinguishable.|
|OI-06 · P0|OI corrections|Can OI be corrected after its first publication? If so, describe correction triggers and representation.|Determines whether first-known OI is immutable.|Correction policy and original/corrected example.|R: ordered PIT correction events / C: documented immutable cutoff / N: corrections reconstructible from logs / X: correction behavior unknown.|
|OI-07 · P0|OI historical response|After an OI correction, does the historical API preserve the originally published value and correction event, or return only the current corrected value?|Directly determines PIT usability.|Paired as-of/current response or authoritative policy.|R: original plus timed revisions retained / C: original retained for defined subset/cutoff / N: originals recoverable from another supported feed / X: corrected-current only.|
|OI-08 · P0|OI revision timestamp|Is there a revision/correction timestamp and does it mean provider receipt, processing, or client dissemination? Give precision and timezone.|A correction must not be applied before observable.|Field-level documentation and example.|R: exact dissemination/availability time / C: guaranteed upper bound / N: derivable from causal message log / X: absent/unknown.|
|OI-09 · P0|OI as-of reconstruction|What supported method, if any, reconstructs exactly what a client would have seen at 09:30, 10:00, and 11:00 ET on a historical date? Please include a concrete, redacted example if available.|Tests intraday causal reproducibility directly.|Supported query/message sequence with expected as-of outputs.|R: exact as-of retrieval / C: safe delayed/as-of subset / N: complete event log enables reconstruction / X: impossible.|

### Option trades

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|TRD-01 · P0|Trade timestamp|What event does each trade timestamp represent: exchange event, OPRA/SIP, ThetaData receipt, processing, or dissemination? State precision, timezone, DST convention, and whether apparent precision equals actual precision.|An event clock cannot be assumed to be an availability clock.|Field specification and one decoded raw-message example.|R: exact client availability plus event clock / C: guaranteed latency bound / N: availability reconstructible from exposed clocks / X: event-only with no guarantee.|
|TRD-02 · P1|Trade sequence|What does `sequence` mean; is it unique, over what scope (contract/root/channel/day/global), can it reset, and is it stable across historical downloads and reprocessing?|Needed for deterministic order and identity.|Sequence specification and reset/collision examples.|R: unique stable scope/order / C: safe composite-key rule / N: stable order reconstructible from other fields / X: no deterministic identity/order.|
|TRD-03 · P1|Trade lifecycle|How are late reports, corrected, cancelled, and busted trades represented? Are original messages retained with causal timestamps and linkage?|Replay must reproduce state transitions rather than final state.|Condition/correction codes and full lifecycle example.|R: timed immutable lifecycle / C: documented subset excludes unsafe conditions / N: lifecycle reconstructible from exposed messages / X: final-state-only/ambiguous.|
|TRD-04 · P2|Trade delivery anomalies|Can historical results contain duplicate or out-of-order messages? Define ordering guarantees and the supported deduplication identity, without assuming `sequence` is globally unique.|Avoids invented ordering and silent deduplication.|Ordering/deduplication contract and example.|R: total stable order/identity / C: documented partitioned ordering rule / N: ordering rebuildable from clocks/IDs / X: irreducibly ambiguous.|
|TRD-05 · P0|Trade as-of stream|Can a download today reconstruct exactly the trade stream a client had received up to timestamp T? If not, enumerate every possible difference (latency, omissions, corrections, ordering, duplicates, reprocessing).|This is the category-level causal gate.|Written guarantee and reproducible redacted as-of example.|R: exact PIT stream / C: guaranteed causal subset or safe lag / N: complete message log enables reconstruction / X: current snapshot only or unknown differences.|

### Option quotes

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|QTE-01 · P0|Quote timestamp|What event does each quote timestamp represent: exchange, OPRA/SIP, ThetaData receipt, processing, or dissemination? State actual precision, timezone, and DST convention.|Quote event time may precede client availability.|Field specification and decoded message example.|R: exact availability and event clocks / C: guaranteed latency bound / N: availability reconstructible / X: event-only without guarantee.|
|QTE-02 · P1|Quote sequence/order|Is a quote sequence exposed? Define uniqueness/scope/reset/stability, duplicates, out-of-order behavior, corrections, and supported message identity.|Required for deterministic book evolution.|Sequence/order contract and anomaly examples.|R: stable identity/order/corrections / C: safe partitioned rule / N: stream reconstructible / X: ambiguous.|
|QTE-03 · P1|Quote meaning|Are rows exchange-specific quotes, OPRA NBBO, or ThetaData-constructed NBBO? Define exchange/condition fields, bid/ask size units/aggregation, and whether both sides share one source state.|Prevents treating venue quotes as NBBO or misreading sizes.|Schema and worked multi-venue example.|R: exact price/size/source semantics / C: supported restricted subset / N: NBBO reconstructible from causal venue messages / X: semantics insufficient.|
|QTE-04 · P2|Locked/crossed quotes|How are locked or crossed markets represented, filtered, normalized, or revised historically? Are original messages retained?|Filtering can change the state observable then.|Policy and original/output examples.|R: original PIT state and rules / C: deterministic safe exclusion / N: original state reconstructible / X: silent/unknown rewriting.|
|QTE-05 · P0|Quote/NBBO as-of stream|Can historical data reconstruct causally the quote or NBBO known by a ThetaData client up to time T? If not, enumerate differences, including historical revisions.|This is the category-level causal gate.|Written guarantee and reproducible redacted as-of example.|R: exact PIT quote/NBBO stream / C: guaranteed subset or lag / N: causal venue stream allows reconstruction / X: latest snapshot or unknown.|

### Event time versus available time

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|TIM-01 · P0|Clock inventory|For each relevant option trade, option quote, OI, index, Greek, and IV endpoint, which fields—if any—store exchange time, OPRA/SIP time, ThetaData receipt time, processing time, and client dissemination time? Define clock source, precision, timezone/DST, and null behavior.|Maps `event_time` separately from `available_time` for every category.|Endpoint-by-endpoint field matrix and schema/version references.|R: explicit event and client-availability clocks / C: explicit event clock plus safe availability bound / N: complete clocks permit reconstruction / X: critical clocks absent.|
|TIM-02 · P0|Availability guarantee|Where only event time exists, is there a documented maximum delay by product/message type before every client could receive the record, including late/corrected messages? State exclusions and whether it is historical or current-only.|Only a guaranteed upper bound can justify conservative delay.|SLA/specification with scope, dates, and exceptions.|R: exact availability rule / C: conservative guaranteed bound / N: logs reconstruct actual availability / X: no applicable guarantee.|

### Index / SPX

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|IDX-01 · P1|Index timestamp/source|For historical SPX index prices, what does the timestamp mean, what is the source, and are receipt, processing, or dissemination times exposed? State timezone and actual precision.|The underlying must be causally aligned to options.|Field/source specification and sample print.|R: source plus exact availability / C: safe bound / N: availability reconstructible / X: event-only/unknown.|
|IDX-02 · P1|Index resolution/depth|What historical SPX resolutions and date depth are supported (tick and aggregations), and are gaps/coverage flags exposed?|Determines whether required underlying observations exist.|Current entitlement-neutral coverage matrix.|R: required tick coverage with flags / C: documented restricted coverage / N: bars reconstructible from PIT ticks / X: insufficient coverage.|
|IDX-03 · P1|Index revisions/PIT|Can an SPX print downloaded today be treated as exactly the value available to a client at that timestamp? Describe revisions, cancellation/correction representation, and PIT classification.|Prevents revised underlying values from leaking backward.|Revision policy and corrected-print lifecycle.|R: PIT print lifecycle / C: immutable subset/cutoff / N: lifecycle reconstructible / X: latest-only/unknown.|
|IDX-04 · P2|Index/OPRA synchronization|How are SPX index messages temporally related to OPRA option messages? Are they on a common clock/order, or must receipt/dissemination timestamps be compared independently?|Equal printed timestamps do not prove simultaneous availability.|Clock architecture/specification and synchronization tolerance.|R: common causal clock/order / C: guaranteed skew bound / N: compare independent receipt clocks / X: relationship unavailable.|

### Greeks and implied volatility

The public documentation already describes a broad Black-Scholes/bisection
method, per-tick underlying use, default dividend treatment, and default use of
the latest supplied SOFR reported one day later. The unresolved questions are
historical availability, exact inputs/conventions, versions, and recalculation.

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|GRK-01 · P1|Greek/IV availability|Which historical Greeks (explicitly including Gamma) and IV products/endpoints are available, and at what resolution/depth?|Establishes category coverage without assuming plan access.|Current endpoint/capability matrix.|R: required fields and PIT resolution / C: usable restricted subset / N: missing values locally reconstructible / X: unavailable.|
|GRK-02 · P1|Stored vs recalculated|Are historical Greeks/IV stored outputs from the original time or recalculated when requested? Can model/input updates revise prior results?|Determines whether today's value existed then.|Storage/recalculation/version policy and before/after example.|R: original outputs retained / C: fixed-version/cutoff subset / N: full PIT inputs available / X: recalculated without lineage.|
|GRK-03 · P1|Model version/conventions|Identify model/version effective history, expiration clock, day-count/time-to-expiration convention, underlying selection, rate and exact SOFR convention, and dividend treatment for SPX options.|Local equivalence requires versioned conventions, not a generic model name.|Versioned methodology and effective-date changelog.|R: complete versioned method / C: fixed documented subset / N: enough details for labelled local reconstruction / X: material inputs unknown.|
|GRK-04 · P0|Input timing|For every Greek/IV output, are timestamps/identifiers exposed for the option input, underlying input, rate, dividend assumption, model version, compute time, and client availability time?|A derived value is available no earlier than its latest input and computation.|Lineage schema and one complete example.|R: full PIT lineage/availability / C: guaranteed conservative bound / N: all PIT inputs exposed separately / X: missing causal lineage.|
|GRK-05 · P1|Historical identity|Is a Greek/IV downloaded today for T exactly what ThetaData displayed at T? If not, enumerate what can change and whether the old output is recoverable.|Direct category-level PIT test.|Written guarantee plus dated original/current comparison.|R: exact historical output / C: immutable subset/cutoff / N: exact local reconstruction possible from PIT inputs / X: unrecoverable revisions.|

### Contract and symbol history

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|SYM-01 · P1|SPX/SPXW identity|How are historical SPX versus SPXW contracts represented and uniquely identified? Define root normalization and any root changes.|Avoids conflating settlement/listing classes.|Historical symbol schema and examples of both roots.|R: stable unique identity / C: deterministic dated normalization / N: identity reconstructible from metadata / X: ambiguous.|
|SYM-02 · P1|Contract metadata|Are expiration, strike, put/call right, listing time, and delisting time historically versioned? How are corrected contract metadata and effective times represented?|Contract metadata itself can contain future corrections.|Versioned contract schema and correction example.|R: PIT versioned metadata / C: safe effective-date restriction / N: versions reconstructible / X: current metadata only/ambiguous.|
|SYM-03 · P1|Historical 0DTE selection|What supported fields and calendar rules unambiguously identify contracts that were listed and expired on replay date, including holidays and special settlements?|Prevents selection using today's normalized chain or wrong settlement class.|Worked dates, contract identifiers, listing/expiration fields, and calendar source.|R: deterministic PIT identification / C: documented restricted calendar rule / N: chain reconstructible from PIT listings / X: no unambiguous method.|

### Plan and entitlement (no account information)

|ID / priority|Topic|Question|Why it matters|Acceptable evidence|Per-question acceptance criteria (R / C / N / X)|
|---|---|---|---|---|---|
|ENT-01 · P1|Required entitlements|What are the current plan/entitlement names required separately for historical option trades, quotes, OI, Greeks/IV, and SPX index history? No account lookup or change is requested.|Capability must not be inferred from public endpoint labels.|Current official plan-feature matrix.|R: capability entitlement identified / C: documented restricted tier / N: raw entitled inputs replace derived product / X: no supporting entitlement.|
|ENT-02 · P1|Depth/resolution entitlements|For each capability, which entitlement controls historical depth and tick resolution, and what exact limits apply?|A nominal endpoint may not provide needed dates or granularity.|Official limit matrix with effective date.|R: required depth/ticks supported / C: bounded usable date/resolution subset / N: finer data supports local aggregation / X: limits insufficient.|

## Response-ingestion template (human-reviewed evidence ledger)

Copy one block per question. This is a documentation template, not executable
ingestion. A support response must never change a mapping automatically.

```yaml
question_id: ""
provider: "ThetaData"
received_at: ""                 # timezone-aware timestamp
support_channel: ""
support_reference: ""
verbatim_summary: ""            # concise; preserve full response separately
evidence_class: ""
confidence: ""
affected_fields: []
mapping_before: "BLOCKED_UNRESOLVED"
proposed_mapping_after: ""       # READY | READY_WITH_CONSERVATIVE_RULE |
                                  # NEEDS_RECONSTRUCTION | EXCLUDED
temporal_rule: ""
correction_rule: ""
remaining_ambiguity: ""
review_status: "PENDING_HUMAN_REVIEW"
```

Human review must validate authority, endpoint/product scope, applicable dates,
timezone, exceptions, and consistency across answers before proposing a mapping
change. The original evidence and review decision should remain versioned.

## Current blockers (unchanged)

* Option trades and quotes lack confirmed provider/client availability clocks,
  PIT revision behavior, stable identity/order, and complete lifecycle semantics.
* OI lacks an exact per-date availability timestamp or universal safe bound,
  plus correction history and reliable as-of reconstruction.
* SPX index data lacks confirmed availability, revisions, entitlement/depth, and
  causal synchronization with option messages.
* Provider Greeks/IV lack full PIT lineage, effective model versions, exact
  conventions, entitlement, and non-recalculation guarantees.
* SPX/SPXW historical listing and corrected contract metadata are not yet
  certified point-in-time.
* Actual plan capabilities, historical depth, and tick resolution remain
  unknown. Any `UNKNOWN` remains blocking; no critical provider field is READY.

## Short message ready for support (do not send yet)

**Subject:** Point-in-time semantics for historical SPX options data

Hello ThetaData Support,

We are evaluating ThetaData for a point-in-time historical replay of SPX options
for quantitative research. We need to distinguish an event's exchange/OPRA time
from when that record became available to a ThetaData client, and to understand
whether a historical response downloaded today preserves the originally
observable message or the latest revised value.

The attached question table requests endpoint-specific confirmation for option
trades, quotes, open interest, SPX index data, Greeks/IV, contract history, and
current plan entitlements. The highest-priority items are: (1) point-in-time
versus latest-revised behavior; (2) exact or guaranteed OI availability for a
trading session; (3) client-availability timestamps or bounds for trades and
quotes; and (4) correction/cancellation ordering. Where possible, please cite
current documentation or include small redacted schema/message examples.

No account lookup, credential exchange, purchase, or plan change is requested.
Thank you for answering by question ID so that scope and exceptions remain
clear.

Regards,

Quantitative research team

## Exact sending recommendation

After an authorized human verifies that the table contains no account or
strategy information, send the short message and the complete tables together
in **one written ThetaData support ticket**, requesting answers by question ID
and preserving the ticket reference and received timestamp. Do not split P0
questions across channels, do not send credentials, and do not ingest data or
change mappings while awaiting the response. When a written response arrives,
record it with the template above and require human review before any separate
mapping-change proposal.
