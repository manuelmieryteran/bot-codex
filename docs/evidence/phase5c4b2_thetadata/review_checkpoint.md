# Phase 5C-4B.2 — ThetaData real-evidence review

**Status:** `PENDING_HUMAN_REVIEW` · **automatic approvals:** 0 ·
**mapping application:** prohibited · **cutover:** `NO`

## Evidence identity and scope

The provider response is preserved byte-for-byte in `raw_response.md` with
SHA-256 `12d56f13a04f94deb6c74dc53fe16d8f888f4a3ecc2a2fdda81c74d49157728d`.
The author is Eduardo, provider ThetaData, channel support ticket. No absolute
receipt timestamp or ticket identifier was provided; both are therefore
`UNKNOWN`. The trailing relative label `28 min` was preserved but was not
converted into an invented timestamp.

The ledger contains one independent review for every registry ID, even when
several IDs reference the same immutable source fragment. Coverage is 23 fully
answered, 18 partially answered, and 0 wholly unanswered. P0 coverage is
13 full + 5 partial + 0 missing; P1 is 8 + 12 + 0; P2 is 2 + 1 + 0.

## Documentation validation

All 13 linked URLs are on the official `docs.thetadata.us` domain. Public GETs
were attempted without credentials on 2026-10-01. The environment tunnel
returned HTTP 403 before reaching each page, so none of the pages is marked as
verified. Each affected claim remains `PROVIDER_WRITTEN_CONFIRMATION` (or
`AMBIGUOUS` where the statement itself is insufficient); documentation
agreement, silence, and page content remain explicitly unverified. This is not
recorded as a provider contradiction.

## Classification, confidence, contradictions, and ambiguity

The 41 question reviews comprise 35 `PROVIDER_WRITTEN_CONFIRMATION` and 6
`AMBIGUOUS`; no claim is promoted to `DOCUMENTED` because no linked page could
be inspected. Confidence is 23 `MEDIUM` and 18 `LOW`; provider authorship alone
did not produce `HIGH`. No real contradiction was found. In particular, these
are different concepts rather than contradictions:

* a single stored day copy versus absent stored-copy version history;
* exchange event time versus client availability;
* separate OPRA correction records versus provider snapshot revisions;
* an OI message timestamp versus a client-availability timestamp; and
* a historical endpoint versus an output computed at request time.

Critical ambiguity remains in `normally around 06:30`, average latency under
3 ms, an index cadence of `about` one print per second, and SOFR publication
`around` 08:00 the next business day. A mean is not a maximum, and none of
these phrases supplies a causal availability bound.

## Conservative conclusions (A–I)

**A. OI cannot be unblocked.** Its economics, missing/zero behavior, and
chronological rows are much clearer, but the row timestamp is an OPRA event
clock, there is no client clock or pre-open SLA, and corrections have no flag.
The provider's `latest timestamp <= T` rule reconstructs tape state, not proven
client knowledge. Proposed status: `BLOCKED_UNRESOLVED`.

**B. Trade tape cannot be unblocked.** Condition-coded records support tape
causality, but not client-session causality. Sequence wraps, is not globally
unique, timestamp+sequence is not a global identity, and cancels do not link to
originals. Proposed status: `BLOCKED_UNRESOLVED`.

**C. Quote tape cannot be unblocked.** NBBO row semantics are useful, but there
is no sequence, client-availability clock/bound, stable message identity, or
complete locked/crossed and correction lifecycle. Proposed status:
`BLOCKED_UNRESOLVED`.

**D. SPX price cannot be unblocked.** The source and event clock are known, but
the feed is separate from OPRA, has no shared sequence or coverage flags, and
timestamp alignment does not prove simultaneous client availability. Proposed
status: `BLOCKED_UNRESOLVED`.

**E. Provider historical Greeks/IV cannot be unblocked as PIT output.** They are
computed when requested, old outputs are not retained, and methodology or
parameters can alter historical results. Proposed status: `EXCLUDED` from PIT
provider-output use.

**F. Local Greek/IV reconstruction may advance only as separately labelled
design work.** Proposed status: `NEEDS_RECONSTRUCTION`, not READY. It requires
causally eligible option and underlying observations, a versioned local model,
and an explicit causal rate policy. Same-date historical SOFR learned on the
next business day is non-causal for that intraday session by default.

**G. Blocked fields** are OI, trades, quotes, SPX, and account entitlement.
Provider historical Greeks/IV are excluded; local Greeks/IV still need
reconstruction. A restricted activity-evidenced historical 0DTE universe and
the provider capability matrix are proposals only, never applied mappings.

**H. Explicit latency policy is required** for trade, quote, SPX/index, OI,
and every local derived value whose latest input comes from one of those
streams. It must be a separately approved conservative policy; the reported
average under 3 ms cannot serve as a bound.

**I. No ID is wholly unanswered, but 18 remain partially answered:** PIT-01,
PIT-02, PIT-03, PIT-04, OI-02, OI-06, OI-09, TRD-03, TRD-04, QTE-02, QTE-04,
IDX-02, IDX-03, IDX-04, GRK-03, GRK-04, SYM-02, and SYM-03. Their remaining
questions concern exact stored-copy revision guarantees, holiday rules, OI
correction identity and client-as-of semantics, duplicate/order guarantees,
locked/crossed lifecycle, index correction/coverage/skew, effective model
history and complete causal lineage, and PIT listing/metadata history.

## Symbology and entitlements

SPX and SPXW remain separate roots; the identity tuple is symbol, expiration,
strike, and right. The ledger records the SPXPM 2018-12-21 cutoff, the
pre-2022-05-16 Monday/Wednesday/Friday SPXW schedule, and SPX AM settlement.
Because metadata is not versioned and listing/delisting timestamps are absent,
the proposed `READY_WITH_CONSERVATIVE_RULE` universe is restricted to SPXW
contracts actually evidenced by a trade or quote on D with expiration D. It
retains inactivity/survivorship and calendar risk and requires human review.

The exact Value/Standard/Pro option and separate Indices capabilities stated by
support are recorded in the raw evidence and ledger. They establish provider
capability only. This account's entitlement is `UNKNOWN`; no lookup, purchase,
or plan recommendation occurred.

## Human decisions required next

1. Accept or reject each proposal independently; none may be batch-approved.
2. Decide whether OI remains excluded or whether a separately evidenced safe
   availability bound will be required from ThetaData.
3. Approve or reject explicit latency/skew policies for tape, quote, index, and
   derived inputs; do not use the 3 ms mean as a bound.
4. Decide whether local Greeks/IV reconstruction work is authorized, including
   the causal rate source, model/version retention, and input eligibility.
5. Decide whether the activity-evidenced SPXW universe is acceptable despite
   its stated incompleteness, or request PIT listing history.
6. Independently establish account entitlement before any acquisition work.
7. Revalidate the official documentation from an environment able to access
   the linked public pages.

No mapping, runtime, loader, dataset, replay, backtest, credential, broker,
order, OAuth, cloud resource, approval, or cutover action is part of this
checkpoint.
