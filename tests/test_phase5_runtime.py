"""Genealogy and safety checks for the Phase 5 runtime wiring."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
PHASE4 = ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
PHASE5 = ROOT / "spx_data_FASE5.py"
OFFICIAL_PHASE4_SHA256 = (
    "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023"
)
SHADOW_FILES = (
    "src/bot_spx/execution/shadow_bridge.py",
    "src/bot_spx/execution/shadow_mode.py",
    "src/bot_spx/execution/shadow_submit.py",
    "tests/test_shadow_mode.py",
)


def _tree(path: Path = PHASE5) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignments() -> dict[str, object]:
    values = {}
    for node in _tree().body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return values


def _wrapper_namespace(*, enabled: bool, category_b: bool = False):
    wrapper = next(
        node
        for node in _tree().body
        if isinstance(node, ast.FunctionDef) and node.name == "dispatch_execution"
    )
    namespace: dict[str, object] = {
        "SHADOW_EXECUTION_ENABLED": enabled,
        "CURRENT_SHADOW_RESULT": "UNCHANGED",
        "_LAST_LEGACY_SUBMIT_OBSERVATION": None,
    }
    calls: list[object] = []
    observed = {"ok": True, "reason": "OBSERVED LEGACY SUBMIT"}

    def legacy():
        calls.append("legacy")
        if category_b:
            namespace["_LAST_LEGACY_SUBMIT_OBSERVATION"] = observed
        return {"status": "AUTHORITATIVE"}

    def state(values):
        calls.append("state")
        return SimpleNamespace(
            pending_order_submitted_at=("2026-01-01T10:00:00-05:00" if category_b else None)
        )

    def intent(values):
        calls.append("intent")
        return "INTENT"

    def config(values, *, submission_timestamp):
        calls.append(("config", submission_timestamp))
        return "CONFIG"

    def shadow(*args, **kwargs):
        calls.append(("shadow", args, kwargs))
        return "SHADOW RESULT"

    namespace.update(
        _dispatch_execution_legacy=legacy,
        execution_state_from_legacy=state,
        execution_intent_from_legacy=intent,
        execution_config_from_legacy=config,
        run_dispatch_shadow=shadow,
        NullOrderSubmitPort=lambda: "NULL PORT",
    )
    exec(compile(ast.Module([wrapper], type_ignores=[]), str(PHASE5), "exec"), namespace)
    return namespace, calls, observed


def test_official_phase4_sha256_is_frozen() -> None:
    assert hashlib.sha256(PHASE4.read_bytes()).hexdigest() == OFFICIAL_PHASE4_SHA256


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("EXECUTION_MODE", "DRY_RUN"),
        ("LIVE_ORDER_EXECUTION_ENABLED", False),
        ("ORDER_EXECUTION_ENVIRONMENT", "SIM"),
        ("SHADOW_EXECUTION_ENABLED", False),
    ],
)
def test_phase5_preserves_safe_defaults(name: str, expected: object) -> None:
    assert _assignments()[name] == expected


def test_disabled_shadow_calls_only_authoritative_legacy() -> None:
    namespace, calls, _ = _wrapper_namespace(enabled=False)
    result = namespace["dispatch_execution"]()

    assert result == {"status": "AUTHORITATIVE"}
    assert calls == ["legacy"]
    assert namespace["CURRENT_SHADOW_RESULT"] == "UNCHANGED"


def test_category_a_snapshots_pre_and_post_without_submit_observation() -> None:
    namespace, calls, _ = _wrapper_namespace(enabled=True)
    result = namespace["dispatch_execution"]()

    shadow_call = calls[-1]
    assert result == {"status": "AUTHORITATIVE"}
    assert calls[:4] == ["state", "intent", "legacy", "state"]
    assert ("config", None) in calls
    assert shadow_call[2]["observed_submit_result"] is None


def test_category_b_consumes_only_legacy_submit_observation() -> None:
    namespace, calls, observed = _wrapper_namespace(enabled=True, category_b=True)
    namespace["dispatch_execution"]()

    shadow_call = calls[-1]
    assert ("config", "2026-01-01T10:00:00-05:00") in calls
    assert shadow_call[2]["observed_submit_result"] is observed
    assert shadow_call[2]["submit_port"] == "NULL PORT"


def test_pre_snapshot_error_fails_candidate_closed_but_runs_legacy() -> None:
    namespace, calls, _ = _wrapper_namespace(enabled=True)
    namespace["execution_state_from_legacy"] = lambda values: (_ for _ in ()).throw(RuntimeError())

    assert namespace["dispatch_execution"]() == {"status": "AUTHORITATIVE"}
    assert calls == ["legacy"]
    assert namespace["CURRENT_SHADOW_RESULT"] is None


def test_candidate_error_fails_closed_after_authoritative_legacy() -> None:
    namespace, calls, _ = _wrapper_namespace(enabled=True)
    namespace["run_dispatch_shadow"] = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError())

    assert namespace["dispatch_execution"]() == {"status": "AUTHORITATIVE"}
    assert calls.count("legacy") == 1
    assert namespace["CURRENT_SHADOW_RESULT"] is None


def test_authoritative_legacy_error_is_not_swallowed() -> None:
    namespace, _, _ = _wrapper_namespace(enabled=True)
    namespace["_dispatch_execution_legacy"] = lambda: (_ for _ in ()).throw(ValueError("legacy"))

    with pytest.raises(ValueError, match="legacy"):
        namespace["dispatch_execution"]()


@pytest.mark.parametrize("enabled", [False, True])
def test_legacy_dispatch_runs_exactly_once(enabled: bool) -> None:
    namespace, calls, _ = _wrapper_namespace(enabled=enabled)
    namespace["dispatch_execution"]()
    assert calls.count("legacy") == 1


@pytest.mark.parametrize(
    "module_name",
    [
        "bot_spx.execution.shadow_bridge",
        "bot_spx.execution.shadow_mode",
        "bot_spx.execution.shadow_submit",
    ],
)
def test_runtime_imports_only_approved_shadow_modules(module_name: str) -> None:
    imports = {
        node.module
        for node in _tree().body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert module_name in imports


def test_existing_shadow_files_are_outside_phase5_change_surface() -> None:
    assert all((ROOT / path).is_file() for path in SHADOW_FILES)
    assert len(SHADOW_FILES) == 4


def test_candidate_has_no_transport_call_or_submit_capability() -> None:
    wrapper = next(
        node
        for node in _tree().body
        if isinstance(node, ast.FunctionDef) and node.name == "dispatch_execution"
    )
    calls = {
        node.func.id
        for node in ast.walk(wrapper)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "submit_tradestation_order" not in calls
    assert "requests" not in calls
    assert "run_dispatch_shadow" in calls
