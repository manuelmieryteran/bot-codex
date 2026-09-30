"""Isolated shadow execution that can never replace the legacy decision."""

from dataclasses import dataclass
from typing import Any

from bot_spx.execution.dispatch import complete_submit_effect, dispatch_transition
from bot_spx.execution.dispatch_models import (
    DispatchConfig,
    DispatchTransition,
    ExecutionIntent,
    ExecutionState,
)
from bot_spx.execution.shadow_submit import NullOrderSubmitPort, ShadowSubmitRecord


@dataclass(frozen=True)
class ShadowMismatch:
    field: str
    legacy: object
    candidate: object


@dataclass(frozen=True)
class ShadowDispatchResult:
    legacy_result: dict[str, Any]
    candidate_transition: DispatchTransition
    candidate_accepted: bool
    mismatches: tuple[ShadowMismatch, ...]
    submit_record: ShadowSubmitRecord | None


def run_dispatch_shadow(
    state: ExecutionState,
    intent: ExecutionIntent,
    config: DispatchConfig,
    *,
    legacy_state: ExecutionState,
    legacy_result: dict[str, Any],
    submit_port: NullOrderSubmitPort,
    observed_submit_result: dict[str, Any] | None = None,
) -> ShadowDispatchResult:
    """Run the candidate without affecting the authoritative legacy outcome."""
    candidate = dispatch_transition(state, intent, config)
    submit_record = None

    if candidate.effect.kind == "SUBMIT_ORDER":
        submit_record = submit_port.record(candidate.effect)
        if observed_submit_result is None:
            mismatch = ShadowMismatch(
                "observed_submit_result",
                "AVAILABLE",
                "MISSING",
            )
            return ShadowDispatchResult(
                legacy_result,
                candidate,
                False,
                (mismatch,),
                submit_record,
            )
        candidate = complete_submit_effect(
            candidate.state,
            intent,
            "EXECUTION SAFETY CHECK PASSED",
            observed_submit_result,
        )

    mismatches = []
    if candidate.state != legacy_state:
        mismatches.append(ShadowMismatch("state", legacy_state, candidate.state))
    if candidate.result != legacy_result:
        mismatches.append(
            ShadowMismatch("result", legacy_result, candidate.result)
        )

    return ShadowDispatchResult(
        legacy_result,
        candidate,
        not mismatches,
        tuple(mismatches),
        submit_record,
    )
