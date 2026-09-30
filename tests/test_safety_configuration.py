"""Pruebas estáticas de los seguros de ejecución del baseline de Fase 4.

El análisis AST evita importar el baseline y, por diseño, no puede hacer
requests, iniciar ThetaData ni enviar órdenes a TradeStation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPOSITORY_ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"


@pytest.fixture(scope="module")
def baseline_tree() -> ast.Module:
    source = BASELINE_PATH.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(BASELINE_PATH))


def _module_assignment(tree: ast.Module, name: str) -> ast.expr:
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return statement.value
    pytest.fail(f"No se encontró la constante requerida {name}")


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef) and statement.name == name:
            return statement
    pytest.fail(f"No se encontró la función requerida {name}")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("EXECUTION_MODE", "DRY_RUN"),
        ("LIVE_ORDER_EXECUTION_ENABLED", False),
        ("ORDER_EXECUTION_ENVIRONMENT", "SIM"),
    ],
)
def test_each_execution_safety_constant_is_frozen(
    baseline_tree: ast.Module,
    name: str,
    expected: object,
) -> None:
    assert ast.literal_eval(_module_assignment(baseline_tree, name)) == expected


def test_sim_environment_selects_only_the_sim_api_base_url(
    baseline_tree: ast.Module,
) -> None:
    function = _function(baseline_tree, "get_tradestation_api_base_url")
    branches = [statement for statement in function.body if isinstance(statement, ast.If)]

    assert len(branches) >= 2
    sim_branch = branches[1]
    assert ast.dump(sim_branch.test, include_attributes=False) == ast.dump(
        ast.Compare(
            left=ast.Name(id="ORDER_EXECUTION_ENVIRONMENT", ctx=ast.Load()),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value="SIM")],
        ),
        include_attributes=False,
    )
    assert len(sim_branch.body) == 1
    assert isinstance(sim_branch.body[0], ast.Return)
    assert isinstance(sim_branch.body[0].value, ast.Name)
    assert sim_branch.body[0].value.id == "TS_SIM_API_BASE_URL"


def test_order_submission_retains_fail_closed_guards_before_any_request(
    baseline_tree: ast.Module,
) -> None:
    function = _function(baseline_tree, "submit_tradestation_order")
    request_statement_index = next(
        index
        for index, statement in enumerate(function.body)
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "tradestation_request"
            for node in ast.walk(statement)
        )
    )

    pre_request_statements = function.body[:request_statement_index]
    guards = [statement for statement in pre_request_statements if isinstance(statement, ast.If)]
    rendered_guards = [ast.unparse(guard.test) for guard in guards]

    assert "not LIVE_ORDER_EXECUTION_ENABLED" in rendered_guards
    assert "ORDER_EXECUTION_ENVIRONMENT != 'SIM'" in rendered_guards

    for required_reason in (
        "LIVE ORDER EXECUTION DISABLED",
        "ORDER EXECUTION ENVIRONMENT NOT SIM",
    ):
        assert any(
            isinstance(node, ast.Constant) and node.value == required_reason
            for guard in guards
            for node in ast.walk(guard)
        )


def test_safety_suite_contains_no_network_or_baseline_imports() -> None:
    """Documenta y hace verificable el alcance estrictamente estático del paso 1C."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden_import_roots = {
        "requests",
        "thetadata",
        "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO",
    }

    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots.isdisjoint(forbidden_import_roots)

