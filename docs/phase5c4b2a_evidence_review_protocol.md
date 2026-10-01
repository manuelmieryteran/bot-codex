# Phase 5C-4B.2A — offline provider-evidence review protocol

## Scope and invariant

This phase prepares an offline review path while the ThetaData response is
absent. It contains no real provider response or dataset, network/API client,
credentials, loader, replay, backtest, runtime integration, mapping mutation,
or approval action. The invariant is absolute: **provider evidence can produce
only a proposal; it can never apply a mapping**.

## Evidence lifecycle

1. Preserve the received response as immutable bytes and record the explicit
   encoding used to create them. Keep raw response, verbatim summary, and
   reviewer interpretation in distinct fields.
2. Scope shared source fragments to individual approved question IDs. Validate
   the expected provider and exact category, and reject unknown IDs, duplicate
   answers, or category mismatches.
3. Classify each question-scoped record as `DOCUMENTED`,
   `PROVIDER_WRITTEN_CONFIRMATION`, `INFERRED`, `CONTRADICTORY`, `AMBIGUOUS`, or
   `UNKNOWN`. Arbitrary strings are impossible because these are enum values.
4. Assess confidence as `HIGH`, `MEDIUM`, `LOW`, or `UNASSESSED` using exactness,
   supporting documentation, timestamp, corrections, point-in-time semantics,
   and ambiguous language. Provider authorship alone never implies `HIGH`.
5. Run matching, ambiguity, contradiction, coverage, and fail-closed promotion
   checks. Emit a deterministic question-ordered ledger and coverage report.
6. Submit proposals to a separate human review. Every record starts
   `PENDING_HUMAN_REVIEW`; every proposal has `requires_human_review=True`.

`UNKNOWN`, `AMBIGUOUS`, and `CONTRADICTORY` evidence blocks promotion.
`INFERRED` evidence alone cannot promote a critical field. Missing P0 answers
prevent affected-field promotion. Missing correction semantics prevents PIT
eligibility; unresolved availability prevents causal replay. The review result
can only be `INCOMPLETE`, `BLOCKED`, or `READY_FOR_HUMAN_REVIEW`, never approved.

## Ambiguity and contradiction

The language detector flags `approximately`, `typically`, `usually`,
`generally`, `normally`, `may`, `can`, `often`, `around`, and `as available`.
Such language is not globally disqualifying, but it blocks when it touches
availability, corrections, or PIT semantics. Contradictions are represented as
incompatible values for the same structured semantic claim, whether the
sources are existing 5C-4B documentation or one or more written responses.
Conflicting records are classified `CONTRADICTORY`; the engine does not choose
a winner.

## Category promotion requirements

* **OI:** reference date, exact/guaranteed availability, late or missing
  publication behavior, corrections/revisions, PIT retention, and historical
  as-of reconstruction must all be supported. Approximate timing such as
  “normally available around 6:30” remains blocked.
* **Trades and quotes:** timestamp meaning, receipt/availability or an equivalent
  guarantee, corrections/cancellations, sequence/order, and historical revision
  policy are all required. Missing corrections or availability blocks `READY`.
* **Greeks/IV:** provider historical values and local reconstruction are distinct
  outcomes. Method documentation without PIT persistence cannot make provider
  values ready. Complete documented option, underlying, rate, dividend, model
  version, and input-timing inputs may propose `NEEDS_RECONSTRUCTION` only.

Possible proposals are `READY`, `READY_WITH_CONSERVATIVE_RULE`,
`NEEDS_RECONSTRUCTION`, `BLOCKED_UNRESOLVED`, and `EXCLUDED`. There is no
function that applies them. A future approval and mapping edit must be explicit,
separate, human-reviewed work.

## Procedure when the real written response arrives

1. Do not place the response in this preparatory commit and do not change a
   mapping. Create separate authorized review work from the then-canonical base.
2. Preserve the original response bytes outside summaries, record encoding,
   timezone-aware receipt time, channel, ticket reference, source documents,
   and stable fragment identifiers. Never add credentials or account details.
3. Create one record per question ID. If one paragraph answers several IDs,
   reference the same preserved fragment from each record; do not merge their
   reviews. Reject IDs, providers, or categories that do not match the registry.
4. Record a verbatim summary separately from model/human interpretation. Assign
   classification, confidence, semantic dimensions/claims, affected fields,
   temporal/correction rules, and remaining ambiguity without assuming facts.
5. Run the complete offline suite. Inspect missing P0 answers, contradictions,
   ambiguity, blocked proposals, coverage, and the deterministic ledger.
6. Have an authorized human review authority, endpoint/product/date scope,
   timezone, exceptions, and every proposal. `READY_FOR_HUMAN_REVIEW` is not
   approval.
7. If approval is granted later, record it as a separate explicit action and
   implement any mapping change in a separate change set with its own tests and
   audit trail. Never feed a proposal directly into current mappings.
