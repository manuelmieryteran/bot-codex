"""Genealogy and safety contract for the separate Phase 5 runtime."""

from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PHASE4 = ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
PHASE5 = ROOT / "spx_data_FASE5.py"
OFFICIAL_SHA256 = "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023"
PHASE5_SHA256 = hashlib.sha256(PHASE5.read_bytes()).hexdigest()
IS_GENESIS = PHASE5_SHA256 == OFFICIAL_SHA256


def _assignments(path: Path) -> dict[str, object]:
    values: dict[str, object] = {}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = ast.literal_eval(statement.value)
        except (TypeError, ValueError):
            pass
    return values


def test_phase5_genesis_files_and_official_oracle_are_present() -> None:
    assert PHASE4.is_file()
    assert PHASE5.is_file()
    assert hashlib.sha256(PHASE4.read_bytes()).hexdigest() == OFFICIAL_SHA256


def test_phase5_genesis_is_byte_identical_before_wiring() -> None:
    commits = subprocess.check_output(
        [
            "git",
            "log",
            "--format=%H",
            "--grep=^Create byte-identical Phase 5 runtime genesis$",
            "--",
            PHASE5.name,
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert len(commits) == 1
    genesis = subprocess.check_output(
        ["git", "show", f"{commits[0]}:{PHASE5.name}"],
        cwd=ROOT,
    )
    assert genesis == PHASE4.read_bytes()
    assert hashlib.sha256(genesis).hexdigest() == OFFICIAL_SHA256


def test_phase5_initial_safety_configuration_matches_oracle() -> None:
    expected = {
        "EXECUTION_MODE": "DRY_RUN",
        "LIVE_ORDER_EXECUTION_ENABLED": False,
        "ORDER_EXECUTION_ENVIRONMENT": "SIM",
    }
    assert {key: _assignments(PHASE4)[key] for key in expected} == expected
    assert {key: _assignments(PHASE5)[key] for key in expected} == expected


def test_phase5_compiles_without_execution() -> None:
    compile(PHASE5.read_text(encoding="utf-8"), str(PHASE5), "exec")


WIRING_FUNCTIONS = {
    "_capture_shadow_execution_snapshot",
    "_observed_submit_result_from_legacy",
    "_shadow_error_telemetry",
    "_observe_legacy_dispatch",
    "dispatch_execution_with_shadow",
}
SNAPSHOT_KEYS = (
    "CURRENT_BROKER_ACCOUNT_ID",
    "CURRENT_BROKER_POSITION_AVAILABLE",
    "CURRENT_BROKER_POSITION_REASON",
    "CURRENT_POSITION_RECONCILIATION_OK",
    "CURRENT_POSITION_RECONCILIATION_ACTION",
    "CURRENT_POSITION_RECONCILIATION_REASON",
    "CURRENT_BROKER_ORDER_STATE",
    "CURRENT_BROKER_ORDER_ID",
    "CURRENT_BROKER_ORDER_STATUS",
    "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION",
    "CURRENT_DISPATCH_STATUS",
    "CURRENT_DISPATCH_REASON",
    "CURRENT_DISPATCH_ID",
    "CURRENT_POSITION_STATE",
    "CURRENT_POSITION_CONTRACTS",
    "CURRENT_POSITION_ENTRY_SIDE",
    "LAST_DISPATCH_SIGNATURE",
    "CURRENT_PENDING_ORDER_ACTION",
    "CURRENT_PENDING_ORDER_SIDE",
    "CURRENT_PENDING_ORDER_QUANTITY",
    "CURRENT_PENDING_ORDER_SYMBOL",
    "CURRENT_PENDING_ORDER_SUBMITTED_AT",
    "CURRENT_EXECUTION_STATUS",
    "CURRENT_EXECUTION_ACTION",
    "CURRENT_EXECUTION_SIDE",
    "CURRENT_EXECUTION_QUANTITY",
    "CURRENT_EXECUTION_SYMBOL",
    "CURRENT_EXECUTION_ORDER_TYPE",
    "CURRENT_EXECUTION_REASON",
    "EXECUTION_MODE",
    "LIVE_ORDER_EXECUTION_ENABLED",
)


def _wiring_namespace(values, *, enabled=True, overrides=None):
    from bot_spx.execution.shadow_bridge import (
        execution_config_from_legacy,
        execution_intent_from_legacy,
        execution_state_from_legacy,
    )
    from bot_spx.execution.shadow_mode import run_dispatch_shadow
    from bot_spx.execution.shadow_submit import NullOrderSubmitPort

    tree = ast.parse(PHASE5.read_text(encoding="utf-8"), filename=str(PHASE5))
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in WIRING_FUNCTIONS
    ]
    assert {node.name for node in functions} == WIRING_FUNCTIONS
    namespace = dict(values)
    namespace.update(
        {
            "SHADOW_EXECUTION_ENABLED": enabled,
            "SHADOW_EXECUTION_SNAPSHOT_KEYS": SNAPSHOT_KEYS,
            "CURRENT_SHADOW_TELEMETRY": {
                "enabled": False,
                "candidate_accepted": False,
                "outcome": "DISABLED",
                "mismatch_fields": (),
                "effect_kind": "NONE",
                "error_type": None,
            },
            "execution_config_from_legacy": execution_config_from_legacy,
            "execution_intent_from_legacy": execution_intent_from_legacy,
            "execution_state_from_legacy": execution_state_from_legacy,
            "run_dispatch_shadow": run_dispatch_shadow,
            "NullOrderSubmitPort": NullOrderSubmitPort,
        }
    )
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(PHASE5), "exec"), namespace)
    namespace.update(overrides or {})
    return namespace


def _legacy_values(**changes):
    from tests.test_shadow_mode import _legacy_values as approved_values

    return approved_values(**changes)


def _attach_oracle(namespace, oracle):
    legacy_results = []

    def dispatch_execution():
        result = oracle.function()
        legacy_results.append(result)
        for name in SNAPSHOT_KEYS:
            if name in oracle.namespace:
                namespace[name] = oracle.namespace[name]
        return result

    namespace["dispatch_execution"] = dispatch_execution
    namespace["_legacy_results"] = legacy_results


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_phase5_flag_is_literal_false_and_not_environment_derived() -> None:
    assignments = _assignments(PHASE5)
    assert assignments["SHADOW_EXECUTION_ENABLED"] is False
    source = PHASE5.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(PHASE5))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "SHADOW_EXECUTION_ENABLED"
            for target in node.targets
        )
    )
    assert isinstance(assignment.value, ast.Constant)
    assert assignment.value.value is False


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_display_snapshot_wires_exactly_one_authoritative_legacy_dispatch() -> None:
    tree = ast.parse(PHASE5.read_text(encoding="utf-8"), filename=str(PHASE5))
    display = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "display_snapshot"
    )
    wrapper_calls = [
        node
        for node in ast.walk(display)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dispatch_execution_with_shadow"
    ]
    wrapper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "dispatch_execution_with_shadow"
    )
    legacy_calls = [
        node
        for node in ast.walk(wrapper)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dispatch_execution"
    ]
    assert len(wrapper_calls) == 1
    assert len(legacy_calls) == 1


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_flag_false_preserves_legacy_result_and_state_without_null_port() -> None:
    from tests.test_shadow_mode import _load_category_a

    values = _legacy_values(CURRENT_EXECUTION_STATUS="IDLE")
    oracle = _load_category_a(values)

    class ForbiddenNullPort:
        def __init__(self):
            raise AssertionError("NULL PORT MUST NOT BE CREATED WHEN SHADOW IS OFF")

    namespace = _wiring_namespace(
        values,
        enabled=False,
        overrides={"NullOrderSubmitPort": ForbiddenNullPort},
    )
    _attach_oracle(namespace, oracle)
    before = {name: namespace[name] for name in SNAPSHOT_KEYS}
    expected = oracle.function()
    expected_post = {
        name: oracle.namespace.get(name, values[name])
        for name in SNAPSHOT_KEYS
    }
    oracle = _load_category_a(values)
    _attach_oracle(namespace, oracle)

    result = namespace["dispatch_execution_with_shadow"]()

    assert result == expected
    assert result is not namespace["CURRENT_SHADOW_TELEMETRY"]
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["outcome"] == "DISABLED"
    assert {name: namespace[name] for name in SNAPSHOT_KEYS} == expected_post
    assert before["CURRENT_POSITION_STATE"] == namespace["CURRENT_POSITION_STATE"]


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
@pytest.mark.parametrize(
    "changes",
    [
        {"CURRENT_EXECUTION_STATUS": "IDLE"},
        {"CURRENT_BROKER_ORDER_STATE": "OPEN"},
        {"EXECUTION_MODE": "DRY_RUN", "LIVE_ORDER_EXECUTION_ENABLED": False},
        {"CURRENT_POSITION_RECONCILIATION_OK": False},
        {"CURRENT_BROKER_ACCOUNT_ID": None},
    ],
    ids=["idle", "broker-open", "dry-run", "safety-block", "payload-block"],
)
def test_flag_true_category_a_matches_without_external_activity(changes) -> None:
    from tests.test_shadow_mode import _load_category_a

    values = _legacy_values(**changes)
    oracle = _load_category_a(values)
    namespace = _wiring_namespace(values)
    _attach_oracle(namespace, oracle)

    result = namespace["dispatch_execution_with_shadow"]()

    assert result is namespace["_legacy_results"][-1]
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["outcome"] == "MATCH"
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["candidate_accepted"] is True
    assert oracle.transport.call_count == 0
    assert oracle.submit.call_count == 0


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
@pytest.mark.parametrize("loader_name", ["failure", "success"])
def test_flag_true_category_b_uses_only_observed_legacy_submit(loader_name) -> None:
    from tests.characterization.legacy_harness import (
        load_dispatch_execution_category_b_failure,
        load_dispatch_execution_category_b_success,
    )
    from bot_spx.execution.shadow_submit import NullOrderSubmitPort

    loader = {
        "failure": load_dispatch_execution_category_b_failure,
        "success": load_dispatch_execution_category_b_success,
    }[loader_name]
    values = _legacy_values()
    oracle = loader()
    ports = []

    class TrackingNullPort(NullOrderSubmitPort):
        def __init__(self):
            super().__init__()
            ports.append(self)

    namespace = _wiring_namespace(values, overrides={"NullOrderSubmitPort": TrackingNullPort})
    _attach_oracle(namespace, oracle)

    result = namespace["dispatch_execution_with_shadow"]()

    assert result is namespace["_legacy_results"][-1]
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["outcome"] == "MATCH"
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["effect_kind"] == "SUBMIT_ORDER"
    assert len(ports) == 1 and len(ports[0].records) == 1
    assert oracle.transport.call_count == 0
    assert oracle.submit.call_count == 1


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_missing_submit_observation_rejects_candidate_and_preserves_legacy() -> None:
    from tests.characterization.legacy_harness import load_dispatch_execution_category_b_success

    values = _legacy_values()
    oracle = load_dispatch_execution_category_b_success()
    namespace = _wiring_namespace(
        values,
        overrides={"_observed_submit_result_from_legacy": lambda result: None},
    )
    _attach_oracle(namespace, oracle)

    result = namespace["dispatch_execution_with_shadow"]()

    assert result is namespace["_legacy_results"][-1]
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["candidate_accepted"] is False
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["outcome"] == "REJECTED"
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["mismatch_fields"] == (
        "observed_submit_result",
    )


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_mismatch_rejects_candidate_without_changing_legacy_result() -> None:
    from tests.test_shadow_mode import _load_category_a

    values = _legacy_values(CURRENT_EXECUTION_STATUS="IDLE")
    oracle = _load_category_a(values)
    namespace = _wiring_namespace(values)
    _attach_oracle(namespace, oracle)
    dispatch = namespace["dispatch_execution"]

    def mismatching_dispatch():
        result = dispatch()
        namespace["CURRENT_POSITION_STATE"] = "LONG"
        namespace["CURRENT_POSITION_CONTRACTS"] = 1
        namespace["CURRENT_POSITION_ENTRY_SIDE"] = "BUY"
        return result

    namespace["dispatch_execution"] = mismatching_dispatch
    result = namespace["dispatch_execution_with_shadow"]()

    assert result is namespace["_legacy_results"][-1]
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["outcome"] == "MISMATCH"
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["candidate_accepted"] is False
    assert "state" in namespace["CURRENT_SHADOW_TELEMETRY"]["mismatch_fields"]


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_shadow_exception_is_caught_only_after_legacy_and_preserves_result() -> None:
    from tests.test_shadow_mode import _load_category_a

    values = _legacy_values(CURRENT_EXECUTION_STATUS="IDLE")
    oracle = _load_category_a(values)

    def exploding_shadow(*args, **kwargs):
        raise RuntimeError("synthetic shadow failure")

    namespace = _wiring_namespace(values, overrides={"run_dispatch_shadow": exploding_shadow})
    _attach_oracle(namespace, oracle)
    result = namespace["dispatch_execution_with_shadow"]()

    assert result is namespace["_legacy_results"][-1]
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["outcome"] == "ERROR"
    assert namespace["CURRENT_SHADOW_TELEMETRY"]["error_type"] == "RuntimeError"


@pytest.mark.skipif(IS_GENESIS, reason="Wiring intentionally belongs to commit B")
def test_phase5_additions_have_no_new_external_capability_or_cutover() -> None:
    phase4_tree = ast.parse(PHASE4.read_text(encoding="utf-8"), filename=str(PHASE4))
    phase5_tree = ast.parse(PHASE5.read_text(encoding="utf-8"), filename=str(PHASE5))
    imports4 = {ast.dump(node) for node in phase4_tree.body if isinstance(node, (ast.Import, ast.ImportFrom))}
    imports5 = [node for node in phase5_tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    added = [node for node in imports5 if ast.dump(node) not in imports4]
    assert all(
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("bot_spx.execution.shadow")
        for node in added
    )
    wiring_source = "\n".join(
        ast.unparse(node)
        for node in phase5_tree.body
        if isinstance(node, ast.FunctionDef) and node.name in WIRING_FUNCTIONS
    ).lower()
    for forbidden in ("requests", "http", "socket", "oauth", "tradestation", "token", "post(", "cutover"):
        assert forbidden not in wiring_source
    phase4_source = PHASE4.read_text(encoding="utf-8")
    assert "spx_data_FASE5" not in phase4_source
    assert "bot_spx.execution.shadow" not in phase4_source
