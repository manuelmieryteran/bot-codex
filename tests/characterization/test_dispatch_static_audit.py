"""Contrato estructural estático de ``dispatch_execution``.

Este módulo solo lee y analiza AST. No importa el baseline, no compila/ejecuta
la función auditada y no modifica el harness dinámico.
"""

from __future__ import annotations

import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPOSITORY_ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
HARNESS_PATH = Path(__file__).with_name("legacy_harness.py")


def _module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _assignment_lines(function: ast.FunctionDef, name: str) -> list[int]:
    return sorted(
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign))
        for target in (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )
        if isinstance(target, ast.Name) and target.id == name
    )


def _call_lines(function: ast.FunctionDef, name: str) -> list[int]:
    return sorted(
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
    )


def test_dispatch_is_available_only_through_category_a_loader() -> None:
    harness_tree = _module(HARNESS_PATH)
    assignments = {
        target.id: node.value
        for node in harness_tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    allowed = ast.literal_eval(assignments["ALLOWED_FUNCTIONS"].args[0])
    function_names = {
        node.name for node in harness_tree.body if isinstance(node, ast.FunctionDef)
    }

    assert "dispatch_execution" in allowed
    assert "load_dispatch_execution" not in function_names
    assert "load_dispatch_execution_category_a" in function_names
    assert "load_dispatch_execution_category_b_failure" in function_names
    assert "load_dispatch_execution_category_b_success" in function_names


def test_category_b_loader_excludes_real_submit_and_injects_recording_fake() -> None:
    harness_tree = _module(HARNESS_PATH)
    for loader_name in (
        "load_dispatch_execution_category_b_failure",
        "load_dispatch_execution_category_b_success",
    ):
        loader = _function(harness_tree, loader_name)
        extracted_names = {
            element.value
            for node in ast.walk(loader)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_extract_allowed_functions"
            and node.args
            and isinstance(node.args[0], ast.Tuple)
            for element in node.args[0].elts
            if isinstance(element, ast.Constant)
        }
        injected_submit_values = [
            value
            for node in ast.walk(loader)
            if isinstance(node, ast.Dict)
            for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant)
            and key.value == "submit_tradestation_order"
        ]

        assert "submit_tradestation_order" not in extracted_names
        assert len(injected_submit_values) == 1
        assert isinstance(injected_submit_values[0], ast.Name)
        assert injected_submit_values[0].id == "recording_submit"


def test_dispatch_global_declarations_and_actual_writes_are_frozen() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    declared = {
        name
        for node in ast.walk(function)
        if isinstance(node, ast.Global)
        for name in node.names
    }
    assigned = {
        target.id
        for node in ast.walk(function)
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign))
        for target in (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
        )
        if isinstance(target, ast.Name)
    }

    assert declared == {
        "LAST_DISPATCH_SIGNATURE",
        "CURRENT_POSITION_STATE",
        "CURRENT_POSITION_CONTRACTS",
        "CURRENT_POSITION_ENTRY_SIDE",
        "CURRENT_BROKER_ORDER_STATE",
        "CURRENT_PENDING_ORDER_ACTION",
        "CURRENT_PENDING_ORDER_SIDE",
        "CURRENT_PENDING_ORDER_QUANTITY",
        "CURRENT_PENDING_ORDER_SYMBOL",
        "CURRENT_PENDING_ORDER_SUBMITTED_AT",
    }
    assert assigned & declared == declared - {"CURRENT_BROKER_ORDER_STATE"}


def test_dispatch_internal_call_order_is_frozen() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    ordered_calls = sorted(
        (
            node.lineno,
            node.func.id,
        )
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id
        in {
            "execution_safety_check",
            "build_tradestation_order_payload",
            "validate_tradestation_order_payload",
            "submit_tradestation_order",
        }
    )

    assert [name for _, name in ordered_calls] == [
        "execution_safety_check",
        "build_tradestation_order_payload",
        "validate_tradestation_order_payload",
        "submit_tradestation_order",
    ]


def test_dispatch_top_level_guardrail_order_is_frozen() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    conditions = [
        ast.unparse(node.test)
        for node in function.body
        if isinstance(node, ast.If)
    ]

    assert conditions == [
        "CURRENT_EXECUTION_STATUS != 'READY'",
        "CURRENT_BROKER_ORDER_STATE in ('OPEN', 'UNKNOWN')",
        "CURRENT_EXECUTION_ACTION == 'ENTRY' and CURRENT_POSITION_STATE != 'FLAT'",
        "CURRENT_EXECUTION_ACTION == 'EXIT' and CURRENT_POSITION_STATE == 'FLAT'",
        "dispatch_signature == LAST_DISPATCH_SIGNATURE",
        "EXECUTION_MODE == 'DRY_RUN'",
        "not safety_ok",
        "not payload_valid",
    ]


def test_dispatch_signature_fields_are_frozen() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    signature_assignment = next(
        node
        for node in function.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "dispatch_signature"
    )

    assert isinstance(signature_assignment.value, ast.Tuple)
    assert [ast.unparse(element) for element in signature_assignment.value.elts] == [
        "CURRENT_EXECUTION_ACTION",
        "CURRENT_EXECUTION_SIDE",
        "CURRENT_EXECUTION_QUANTITY",
        "CURRENT_EXECUTION_REASON",
    ]


def test_dry_run_precedes_safety_block_and_payload_calls() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    top_level_ifs = [node for node in function.body if isinstance(node, ast.If)]
    dry_run_line = next(
        node.lineno
        for node in top_level_ifs
        if ast.unparse(node.test) == "EXECUTION_MODE == 'DRY_RUN'"
    )
    safety_block_line = next(
        node.lineno
        for node in top_level_ifs
        if ast.unparse(node.test) == "not safety_ok"
    )

    assert dry_run_line < safety_block_line
    assert dry_run_line < _call_lines(function, "build_tradestation_order_payload")[0]
    assert dry_run_line < _call_lines(function, "submit_tradestation_order")[0]


def test_pending_state_and_signature_are_written_before_submit() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    submit_line = _call_lines(function, "submit_tradestation_order")[0]

    for name in (
        "LAST_DISPATCH_SIGNATURE",
        "CURRENT_PENDING_ORDER_ACTION",
        "CURRENT_PENDING_ORDER_SIDE",
        "CURRENT_PENDING_ORDER_QUANTITY",
        "CURRENT_PENDING_ORDER_SYMBOL",
        "CURRENT_PENDING_ORDER_SUBMITTED_AT",
    ):
        assert max(_assignment_lines(function, name)) < submit_line


def test_dispatch_returns_only_dicts_with_expected_statuses() -> None:
    function = _function(_module(BASELINE_PATH), "dispatch_execution")
    returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
    literal_statuses = {
        value.value
        for node in returns
        if isinstance(node.value, ast.Dict)
        for key, value in zip(node.value.keys, node.value.values)
        if isinstance(key, ast.Constant)
        and key.value == "status"
        and isinstance(value, ast.Constant)
    }

    assert all(isinstance(node.value, ast.Dict) for node in returns)
    assert literal_statuses == {
        "IDLE",
        "ORDER_BLOCKED",
        "POSITION_BLOCKED",
        "DUPLICATE_BLOCKED",
        "SIMULATED",
        "BLOCKED",
        "PAYLOAD_BLOCKED",
    }
    assert any(
        isinstance(value, ast.IfExp)
        for node in returns
        for key, value in zip(node.value.keys, node.value.values)
        if isinstance(key, ast.Constant) and key.value == "status"
    )
