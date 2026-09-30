"""Auditoría AST del bloque post-dispatch incrustado en display_snapshot."""

from __future__ import annotations

import ast
from pathlib import Path


BASELINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
)


def _display_function() -> ast.FunctionDef:
    tree = ast.parse(
        BASELINE_PATH.read_text(encoding="utf-8"),
        filename=str(BASELINE_PATH),
    )
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "display_snapshot"
    ]
    assert len(matches) == 1
    return matches[0]


def _assigned_names(node: ast.AST) -> set[str]:
    return {
        target.id
        for assignment in ast.walk(node)
        if isinstance(assignment, ast.Assign)
        for target in assignment.targets
        if isinstance(target, ast.Name)
    }


def _submitted_branch() -> ast.If:
    display = _display_function()
    matches = [
        node
        for node in display.body
        if isinstance(node, ast.If)
        and ast.unparse(node.test) == "CURRENT_DISPATCH_STATUS == 'SUBMITTED'"
    ]
    assert len(matches) == 1
    return matches[0]


def test_post_dispatch_reads_dispatch_result_before_submitted_branch() -> None:
    display = _display_function()
    statements = list(display.body)
    dispatch_assignment = next(
        node
        for node in statements
        if isinstance(node, ast.Assign)
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "dispatch_execution"
            for call in ast.walk(node)
        )
    )
    broker_response_assignment = next(
        node
        for node in statements
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "broker_response"
    )
    submitted = _submitted_branch()

    assert dispatch_assignment.lineno < broker_response_assignment.lineno
    assert broker_response_assignment.lineno < submitted.lineno
    assert "dispatch_result.get('broker_response')" == ast.unparse(
        broker_response_assignment.value
    )


def test_submitted_branch_initializes_open_state_and_extracts_order_id_paths() -> None:
    submitted = _submitted_branch()
    source = ast.unparse(submitted)
    assigned = _assigned_names(submitted)

    assert {
        "CURRENT_BROKER_ORDER_ID",
        "CURRENT_BROKER_ORDER_STATUS",
        "CURRENT_BROKER_ORDER_STATE",
        "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION",
    }.issubset(assigned)
    assert "CURRENT_BROKER_ORDER_STATE = 'OPEN'" in source
    assert "CURRENT_BROKER_ORDER_ID = None" in source
    assert "CURRENT_BROKER_ORDER_STATUS = 'SUBMITTED'" in source
    assert "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION = 'PENDING BROKER STATUS'" in source
    assert "orders = broker_response.get('Orders')" in source
    assert "first_order.get('OrderID')" in source
    assert "broker_response.get('OrderID')" in source
    assert "first_order.get('Status', first_order.get('OrderStatus', 'SUBMITTED'))" in source
    assert "broker_response.get('Status', broker_response.get('OrderStatus', 'SUBMITTED'))" in source


def test_submitted_branch_does_not_mutate_pending_or_position_state() -> None:
    submitted = _submitted_branch()
    assigned = _assigned_names(submitted)

    assert assigned.isdisjoint(
        {
            "CURRENT_PENDING_ORDER_ACTION",
            "CURRENT_PENDING_ORDER_SIDE",
            "CURRENT_PENDING_ORDER_QUANTITY",
            "CURRENT_PENDING_ORDER_SYMBOL",
            "CURRENT_PENDING_ORDER_SUBMITTED_AT",
            "CURRENT_POSITION_STATE",
            "CURRENT_POSITION_CONTRACTS",
            "CURRENT_POSITION_ENTRY_SIDE",
        }
    )

