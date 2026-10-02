# Phase 5C-4B.4C-2C — controlled account-verification evidence review

## Evidence origin and boundary

This offline checkpoint preserves the sanitized result supplied inline from the
**second authorized human local execution** for `2026-01-15`. That execution used
the corrected transport through ThetaData's official `ThetaClient`. The source
is preserved as `probe_result_v2.json`; its SHA-256 is
`af908e2213baa028ac7a501483221a00cb50305aef59ecce044c9bd466dc00a0`.
Only the sanitized evidence was ingested. This review made no ThetaData call,
read no credential, ran no probe, downloaded no dataset or provider payload,
and performed no TradeStation, order, DigitalOcean, runtime, or backtest action.

## Deterministic result

| Probe | Capability | Outcome | Status | Interpretation |
|---|---|---|---|---|
| P1 | Account metadata | `VERIFIED_AVAILABLE` | `SUCCESS` | Metadata access verified; subscription field values were not persisted, so account tier remains `UNRESOLVED`. |
| P2 | SPX/SPXW contract list | `VERIFIED_AVAILABLE` | `SUCCESS` | Access/schema observed for the tested date only; scope anomaly recorded below. |
| P3 | Option quote | `VERIFIED_AVAILABLE` | `SUCCESS` | Acquisition for the tested contract/date only; quote causal mapping remains blocked. |
| P4 | Option trade | `AMBIGUOUS` | `EMPTY_SUCCESS` | Zero rows cannot distinguish no trades, window, method behavior, entitlement, or another unproved cause. |
| P5 | Open interest | `VERIFIED_AVAILABLE` | `SUCCESS` | Acquisition only; OI causal mapping remains blocked. |
| P6 | IV/first-order Greeks | `VERIFIED_AVAILABLE` | `SUCCESS` | Acquisition only; provider outputs remain excluded from causal replay. |
| P7 | EOD Gamma | `VERIFIED_AVAILABLE` | `SUCCESS` | Does not establish intraday/per-trade Gamma or complete local reconstruction; P6 and P7 are independent. |
| P8 | SPX index history | `ERROR` | `TRANSPORT_ERROR` | Entitlement remains `UNRESOLVED`; Options access does not imply Indices access. |
| P9 | Interest-rate history | `VERIFIED_AVAILABLE` | `SUCCESS` | Acquisition only; retrospective access does not establish causal intraday availability. |

Derived outcome counts in the fixed order available/denied/ambiguous/not-tested/error
are **7/0/1/0/1**.

## Scope anomaly and historical-depth limit

P2 is classified `ACQUISITION_SCOPE_ANOMALY`: a probe intended as a minimal
contract verification transiently observed **17,326 rows**. No market or contract
values were persisted in the sanitized evidence and `raw_payloads_persisted=0`.
This is not a secret leak, raw-payload persistence, causal mapping promotion,
backtest, or runtime integration. P2 must not be repeated automatically; any
future real contract verification requires a stricter limit designed in advance.

Every P1–P9 result establishes at most `SINGLE_DATE_ONLY` historical depth. It
does not establish complete account history, a point-in-time listed universe,
versioned metadata, absence of survivorship, or causal replay eligibility.

## Readiness versus causality

Acquisition availability is not causal replay eligibility. Account evidence,
provider capability, acquisition readiness, and causal mapping remain separate.
The existing mappings are unchanged:

- provider Greeks/IV: `EXCLUDED`;
- local Greeks/IV: `NEEDS_RECONSTRUCTION`;
- SPX, OI, trades, and quotes: `BLOCKED_UNRESOLVED`;
- historical SPXW 0DTE universe: `READY_WITH_CONSERVATIVE_RULE / LOW`.

The rate publication/availability and SOFR D/D+1 no-look-ahead rules remain
unchanged. There were zero mapping promotions and zero runtime modifications.
No credentials are present. No new provider calls or probes were made, no
backtest was run, and `cutover=NO`.
