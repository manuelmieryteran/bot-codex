"""Alarmas de integridad para el baseline oficial e inmutable de Fase 4.

Estas pruebas leen y analizan el archivo como texto. No importan ni ejecutan el
módulo, por lo que no inicializan clientes ni realizan actividad de red.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPOSITORY_ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
OFFICIAL_SHA256 = "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023"
EXPECTED_SAFETY_CONFIGURATION = {
    "EXECUTION_MODE": "DRY_RUN",
    "LIVE_ORDER_EXECUTION_ENABLED": False,
    "ORDER_EXECUTION_ENVIRONMENT": "SIM",
}


def _baseline_source() -> str:
    return BASELINE_PATH.read_text(encoding="utf-8")


def _literal_module_assignments(source: str) -> dict[str, object]:
    assignments: dict[str, object] = {}
    tree = ast.parse(source, filename=str(BASELINE_PATH))

    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            assignments[target.id] = ast.literal_eval(statement.value)
        except (ValueError, TypeError):
            continue

    return assignments


def test_official_baseline_exists() -> None:
    assert BASELINE_PATH.is_file(), f"No existe el baseline oficial: {BASELINE_PATH}"


def test_official_baseline_sha256_is_unchanged() -> None:
    digest = hashlib.sha256(BASELINE_PATH.read_bytes()).hexdigest()
    assert digest == OFFICIAL_SHA256


def test_official_baseline_compiles_without_importing_it() -> None:
    source = _baseline_source()
    compile(source, str(BASELINE_PATH), "exec")


def test_critical_safety_constants_remain_exact() -> None:
    assignments = _literal_module_assignments(_baseline_source())
    observed = {
        name: assignments.get(name)
        for name in EXPECTED_SAFETY_CONFIGURATION
    }
    assert observed == EXPECTED_SAFETY_CONFIGURATION

