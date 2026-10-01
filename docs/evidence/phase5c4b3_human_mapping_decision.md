# FASE 5C-4B.3 — Human mapping decision

**Decision date:** 2026-10-01
**Human mapping decision status:** `HUMAN_APPROVED` (only for the nine
decisions below)
**Evidence review status:** unchanged at `PENDING_HUMAN_REVIEW`
**Cutover:** `NO`

## Immutable evidence base

The decision is an overlay on
[`phase5c4b2_thetadata/evidence_ledger.json`](phase5c4b2_thetadata/evidence_ledger.json),
whose raw-response SHA-256 is
`12d56f13a04f94deb6c74dc53fe16d8f888f4a3ecc2a2fdda81c74d49157728d`.
Neither that ledger nor `raw_response.md` is modified or globally approved.
The evidence review remains distinct from this human mapping decision.

## Approved decisions

| Subject | Decision | Confidence | Rationale / residual risk |
|---|---|---|---|
| Open interest | `BLOCKED_UNRESOLVED` | LOW | Previous-trading-day semantics and OPRA message time do not establish client availability. There is no pre-09:30 SLA, guaranteed latency bound, or correction flag; multiple rows may exist. |
| Option trades | `BLOCKED_UNRESOLVED` | LOW | Exchange time and wrapping, non-global sequence do not establish receipt time. Cancels/corrections are unlinked tape records. |
| Option quotes | `BLOCKED_UNRESOLVED` | LOW | OPRA NBBO has no sequence, receipt time, or maximum latency bound. |
| SPX historical spot | `BLOCKED_UNRESOLVED` | LOW | The Cboe Global Indices Feed is separate from OPRA, has no shared sequence, and supplies no proven client availability bound. |
| Provider historical Greeks/IV | `EXCLUDED` | MEDIUM | Today's request-time calculations are not preserved historical point-in-time outputs. This does not exclude their inputs. |
| Locally reconstructed Greeks/IV | `NEEDS_RECONSTRUCTION` | LOW | A future deterministic, versioned reconstruction is possible but is not replay-eligible today. |
| Historical SPXW 0DTE universe | `READY_WITH_CONSERVATIVE_RULE` | LOW | On date D require root SPXW, expiration D, and observed trade/quote activity on D. This may omit listed-but-inactive contracts, incomplete historical metadata, or special holiday/listing cases. |
| Provider capability | `READY` | MEDIUM | The support tier table is descriptive provider metadata only. |
| Our account entitlement | `BLOCKED_UNRESOLVED` | LOW | No account-specific evidence exists; the contracted tier is not inferred. |

Local Greeks/IV reconstruction would require causal option price/quote,
causal underlying, causal rate, dividend convention, expiration convention,
model version, input timestamps, and a deterministic implementation. Same-day
SOFR obtained retrospectively is not presumed available intraday before its
publication.

## Safety and scope

No event timestamp is converted into an availability timestamp. The reported
average latency is not a causal guarantee, and **no latency bound is created**.
This phase performs no data ingestion, dataset download, API call, loader or
main execution, OAuth, order, cloud operation, backtest, or runtime cutover.
There is no backtest. Operational Phase 4/Phase 5 files remain untouched.
`cutover=NO`.
