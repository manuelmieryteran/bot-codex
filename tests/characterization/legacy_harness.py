"""Harness mínimo para caracterizar funciones aisladas del baseline de Fase 4.

El harness verifica primero el SHA-256 oficial, extrae por AST únicamente la
definición solicitada y ejecuta solo el bytecode que crea esa función en un
namespace nuevo. No ejecuta imports, asignaciones ni el bloque ``__main__`` del
baseline. En particular, no carga dotenv, ThetaData ni requests, y no lee
credenciales.

La allowlist se limita a las funciones de ejecución enumeradas explícitamente
en ``ALLOWED_FUNCTIONS``. Cuando se carga una función, su transporte se inyecta
siempre como
:class:`ForbiddenTransport`, un sentinel sin capacidad de red que cuenta el
intento y falla inmediatamente si fuese alcanzado.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPOSITORY_ROOT / "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py"
OFFICIAL_SHA256 = "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023"
ALLOWED_FUNCTIONS = frozenset(
    {
        "build_tradestation_order_payload",
        "build_execution_intent",
        "compare_internal_vs_broker_position",
        "dispatch_execution",
        "execution_safety_check",
        "refresh_broker_reconciliation",
        "get_tradestation_api_base_url",
        "get_primary_tradestation_account_id",
        "get_tradestation_accounts",
        "get_tradestation_es_position",
        "get_tradestation_positions",
        "normalize_tradestation_es_position",
        "reconcile_internal_with_broker_position",
        "submit_tradestation_order",
        "update_broker_reconciliation_state",
        "validate_tradestation_order_payload",
        "validate_position_state",
    }
)
NETWORK_SENTINEL_MESSAGE = "NETWORK TRANSPORT MUST NOT BE CALLED"
FIXED_PENDING_TIMESTAMP = "2026-01-01T10:00:00-05:00"
SYNTHETIC_SUBMIT_FAILURE = {
    "ok": False,
    "status_code": 503,
    "reason": "SYNTHETIC SUBMIT FAILURE",
    "response": {"synthetic": True},
}
SYNTHETIC_SUBMIT_SUCCESS = {
    "ok": True,
    "status_code": 200,
    "reason": "SYNTHETIC SUBMIT SUCCESS",
    "response": {
        "Orders": [
            {"OrderID": "SYNTHETIC-ORDER-ID-001"},
        ]
    },
}


class ForbiddenTransport:
    """Sentinel auditable que no implementa ni delega ningún transporte real."""

    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.call_count += 1
        raise AssertionError(NETWORK_SENTINEL_MESSAGE)


class ForbiddenSubmit:
    """Primera barrera: detecta cualquier intento de submit del dispatcher."""

    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, *args: object, **kwargs: object) -> None:
        self.call_count += 1
        raise AssertionError("SUBMIT MUST NOT BE CALLED")


class ForbiddenClock:
    """Reloj fail-closed: categoría A nunca debe preparar pending state."""

    def __init__(self) -> None:
        self.call_count = 0

    def now(self, *args: object, **kwargs: object) -> None:
        self.call_count += 1
        raise AssertionError("PENDING CLOCK MUST NOT BE CALLED")


class RecordingSubmit:
    """Submit local determinista: registra y siempre devuelve fallo sintético."""

    def __init__(self) -> None:
        self.call_count = 0
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        self.payloads.append(payload)
        return {
            "ok": False,
            "status_code": 503,
            "reason": "SYNTHETIC SUBMIT FAILURE",
            "response": {"synthetic": True},
        }


class RecordingSuccessSubmit:
    """Submit local que registra y devuelve un único éxito sintético fijo."""

    def __init__(self) -> None:
        self.call_count = 0
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        self.payloads.append(payload)
        return {
            "ok": True,
            "status_code": 200,
            "reason": "SYNTHETIC SUBMIT SUCCESS",
            "response": {
                "Orders": [
                    {"OrderID": "SYNTHETIC-ORDER-ID-001"},
                ]
            },
        }


class FixedTimestamp:
    """Valor temporal sintético cuya serialización es totalmente fija."""

    def isoformat(self) -> str:
        return FIXED_PENDING_TIMESTAMP


class FixedClock:
    """Reloj local que nunca consulta el tiempo del sistema."""

    def __init__(self) -> None:
        self.call_count = 0

    def now(self, *args: object, **kwargs: object) -> FixedTimestamp:
        self.call_count += 1
        return FixedTimestamp()


class FixedUUIDValue:
    """UUID sintético con el mismo atributo consumido por el bloque legacy."""

    hex = "SYNTHETIC-DISPATCH-ID-001"


class FixedUUIDModule:
    """Sustituto local de ``uuid`` que nunca consulta entropía del sistema."""

    def __init__(self) -> None:
        self.call_count = 0

    def uuid4(self) -> FixedUUIDValue:
        self.call_count += 1
        return FixedUUIDValue()


class DeterministicBrokerLookup:
    """Fake local para account y ES position lookup sin capacidad externa."""

    def __init__(
        self,
        account_id: str | None,
        account_reason: str,
        position_result: dict[str, Any],
    ) -> None:
        self.account_id = account_id
        self.account_reason = account_reason
        self.position_result = position_result
        self.account_call_count = 0
        self.position_call_count = 0
        self.position_account_ids: list[str] = []

    def get_primary_account_id(self) -> tuple[str | None, str]:
        self.account_call_count += 1
        return self.account_id, self.account_reason

    def get_es_position(self, account_id: str) -> dict[str, Any]:
        self.position_call_count += 1
        self.position_account_ids.append(account_id)
        return self.position_result


class SyntheticRequestException(Exception):
    """Error de transporte local reconocido por el código legacy aislado."""


class SyntheticRequests:
    """Namespace mínimo equivalente a ``requests.exceptions``."""

    class exceptions:
        RequestException = SyntheticRequestException


class SyntheticHTTPResponse:
    """Respuesta HTTP sintética sin socket, cliente ni endpoint real."""

    def __init__(
        self,
        status_code: int,
        text: str,
        json_data: Any,
        invalid_json: bool,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.json_data = json_data
        self.invalid_json = invalid_json

    def json(self) -> Any:
        if self.invalid_json:
            raise ValueError("SYNTHETIC INVALID JSON")
        return self.json_data


class DeterministicHTTPTransport:
    """Transporte falso que registra una única forma de request determinista."""

    def __init__(self, response: SyntheticHTTPResponse, fail: bool) -> None:
        self.response = response
        self.fail = fail
        self.call_count = 0
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, method: str, url: str, **kwargs: Any) -> SyntheticHTTPResponse:
        self.call_count += 1
        self.calls.append((method, url, kwargs))
        if self.fail:
            raise SyntheticRequestException("SYNTHETIC TRANSPORT FAILURE")
        return self.response


@dataclass(frozen=True)
class IsolatedLegacyFunction:
    """Función extraída junto con su namespace y sentinel exclusivos."""

    function: Callable[..., Any]
    namespace: dict[str, Any]
    transport: ForbiddenTransport


@dataclass(frozen=True)
class IsolatedCategoryADispatch:
    """Dispatcher aislado con submit, transporte y reloj fail-closed."""

    function: Callable[[], dict[str, Any]]
    namespace: dict[str, Any]
    transport: ForbiddenTransport
    submit: ForbiddenSubmit
    clock: ForbiddenClock


@dataclass(frozen=True)
class IsolatedCategoryBFailureDispatch:
    """Dispatcher aislado para un único submit fallido, local y determinista."""

    function: Callable[[], dict[str, Any]]
    namespace: dict[str, Any]
    transport: ForbiddenTransport
    submit: RecordingSubmit
    clock: FixedClock


@dataclass(frozen=True)
class IsolatedCategoryBSuccessDispatch:
    """Dispatcher aislado para un único submit exitoso y sintético."""

    function: Callable[[], dict[str, Any]]
    namespace: dict[str, Any]
    transport: ForbiddenTransport
    submit: RecordingSuccessSubmit
    clock: FixedClock


@dataclass(frozen=True)
class IsolatedPostDispatch:
    """Bloque post-dispatch exacto con namespace y UUID sintéticos."""

    function: Callable[[], None]
    namespace: dict[str, Any]
    uuid: FixedUUIDModule


@dataclass(frozen=True)
class IsolatedBrokerRefresh:
    """Refresh legacy con lookups resueltos exclusivamente por un fake local."""

    function: Callable[[], tuple[bool, str]]
    namespace: dict[str, Any]
    transport: ForbiddenTransport
    lookup: DeterministicBrokerLookup


@dataclass(frozen=True)
class IsolatedBrokerLookup:
    """Lookup legacy ejecutado contra un transporte HTTP totalmente falso."""

    function: Callable[..., Any]
    namespace: dict[str, Any]
    transport: DeterministicHTTPTransport


def _extract_allowed_functions(
    function_names: tuple[str, ...],
    namespace_values: dict[str, Any],
    exposed_function: str,
) -> IsolatedLegacyFunction:
    """Extrae un conjunto cerrado de funciones exactas a un namespace nuevo."""
    requested = set(function_names)
    if not requested or not requested.issubset(ALLOWED_FUNCTIONS):
        raise ValueError("LEGACY FUNCTION IS NOT ALLOWED BY THE HARNESS")

    baseline_bytes = BASELINE_PATH.read_bytes()
    digest = hashlib.sha256(baseline_bytes).hexdigest()
    if digest != OFFICIAL_SHA256:
        raise RuntimeError("OFFICIAL PHASE 4 BASELINE HASH MISMATCH")

    source = baseline_bytes.decode("utf-8")
    tree = ast.parse(source, filename=str(BASELINE_PATH))
    matches = [
        statement
        for statement in tree.body
        if isinstance(statement, ast.FunctionDef)
        and statement.name in requested
    ]
    matched_names = [function.name for function in matches]
    if len(matches) != len(requested) or set(matched_names) != requested:
        raise RuntimeError("EXPECTED EXACTLY ONE DEFINITION PER ALLOWED FUNCTION")

    if any(function.decorator_list for function in matches):
        raise RuntimeError("DECORATED LEGACY FUNCTION IS NOT SAFE TO EXTRACT")

    isolated_module = ast.fix_missing_locations(
        ast.Module(body=matches, type_ignores=[])
    )
    transport = ForbiddenTransport()
    namespace: dict[str, Any] = {
        # Allowlist mínima requerida por el validador y por la excepción del
        # selector. No se proporciona __import__, open, requests ni clientes.
        "__builtins__": {
            "ValueError": ValueError,
            "TypeError": TypeError,
            "dict": dict,
            "abs": abs,
            "float": float,
            "int": int,
            "isinstance": isinstance,
            "str": str,
            "type": type,
        },
        "tradestation_request": transport,
        **namespace_values,
    }

    exec(compile(isolated_module, str(BASELINE_PATH), "exec"), namespace)

    return IsolatedLegacyFunction(
        function=namespace[exposed_function],
        namespace=namespace,
        transport=transport,
    )


def load_post_dispatch_transition(
    *,
    dispatch_result: dict[str, Any],
    dispatch_status: str,
    dispatch_reason: str,
    dispatch_id: str | None,
    broker_order_id: str | None,
    broker_order_status: str,
    broker_order_state: str,
    broker_order_status_description: str,
) -> IsolatedPostDispatch:
    """Extrae solo los statements que interpretan el resultado de dispatch."""
    baseline_bytes = BASELINE_PATH.read_bytes()
    digest = hashlib.sha256(baseline_bytes).hexdigest()
    if digest != OFFICIAL_SHA256:
        raise RuntimeError("OFFICIAL PHASE 4 BASELINE HASH MISMATCH")

    tree = ast.parse(baseline_bytes.decode("utf-8"), filename=str(BASELINE_PATH))
    displays = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "display_snapshot"
    ]
    if len(displays) != 1:
        raise RuntimeError("EXPECTED EXACTLY ONE DISPLAY SNAPSHOT DEFINITION")

    body = displays[0].body
    start = next(
        index
        for index, node in enumerate(body)
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "CURRENT_DISPATCH_STATUS"
    )
    submitted = next(
        index
        for index, node in enumerate(body)
        if isinstance(node, ast.If)
        and ast.unparse(node.test) == "CURRENT_DISPATCH_STATUS == 'SUBMITTED'"
    )
    extracted = body[start : submitted + 1]
    assigned_names = {
        target.id
        for node in extracted
        for assignment in ast.walk(node)
        if isinstance(assignment, ast.Assign)
        for target in assignment.targets
        if isinstance(target, ast.Name)
    }
    expected_assignments = {
        "CURRENT_DISPATCH_STATUS",
        "CURRENT_DISPATCH_REASON",
        "CURRENT_DISPATCH_ID",
        "broker_response",
        "CURRENT_BROKER_ORDER_ID",
        "CURRENT_BROKER_ORDER_STATUS",
        "CURRENT_BROKER_ORDER_STATE",
        "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION",
        "orders",
        "first_order",
    }
    if assigned_names != expected_assignments:
        raise RuntimeError("POST-DISPATCH BLOCK STRUCTURE CHANGED")

    isolated_module = ast.fix_missing_locations(
        ast.Module(body=extracted, type_ignores=[])
    )
    code = compile(isolated_module, str(BASELINE_PATH), "exec")
    fixed_uuid = FixedUUIDModule()
    namespace: dict[str, Any] = {
        "__builtins__": {
            "dict": dict,
            "isinstance": isinstance,
            "list": list,
            "str": str,
        },
        "dispatch_result": dispatch_result,
        "CURRENT_DISPATCH_STATUS": dispatch_status,
        "CURRENT_DISPATCH_REASON": dispatch_reason,
        "CURRENT_DISPATCH_ID": dispatch_id,
        "CURRENT_BROKER_ORDER_ID": broker_order_id,
        "CURRENT_BROKER_ORDER_STATUS": broker_order_status,
        "CURRENT_BROKER_ORDER_STATE": broker_order_state,
        "CURRENT_BROKER_ORDER_STATUS_DESCRIPTION": (
            broker_order_status_description
        ),
        "uuid": fixed_uuid,
    }

    def run() -> None:
        exec(code, namespace)

    return IsolatedPostDispatch(run, namespace, fixed_uuid)


def load_validate_tradestation_order_payload() -> IsolatedLegacyFunction:
    """Carga únicamente el validador exacto con sus builtins mínimos."""
    return _extract_allowed_functions(
        ("validate_tradestation_order_payload",),
        {},
        "validate_tradestation_order_payload",
    )


def load_normalize_tradestation_es_position() -> IsolatedLegacyFunction:
    """Carga únicamente la normalización pura de posición broker."""
    return _extract_allowed_functions(
        ("normalize_tradestation_es_position",),
        {},
        "normalize_tradestation_es_position",
    )


def load_compare_internal_vs_broker_position(
    *,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
) -> IsolatedLegacyFunction:
    """Carga comparación y normalización con posición interna sintética."""
    return _extract_allowed_functions(
        (
            "compare_internal_vs_broker_position",
            "normalize_tradestation_es_position",
        ),
        {
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
        },
        "compare_internal_vs_broker_position",
    )


def load_reconcile_internal_with_broker_position(
    *,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
) -> IsolatedLegacyFunction:
    """Carga reconciliación pura y sus dependencias exactas."""
    return _extract_allowed_functions(
        (
            "compare_internal_vs_broker_position",
            "normalize_tradestation_es_position",
            "reconcile_internal_with_broker_position",
        ),
        {
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
        },
        "reconcile_internal_with_broker_position",
    )


def load_update_broker_reconciliation_state(
    *,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
    broker_account_id: str | None,
    broker_position_available: bool,
    broker_position_reason: str,
    reconciliation_ok: bool,
    reconciliation_action: str,
    reconciliation_reason: str,
) -> IsolatedLegacyFunction:
    """Carga la actualización de reconciliación sin consultas externas."""
    return _extract_allowed_functions(
        (
            "compare_internal_vs_broker_position",
            "normalize_tradestation_es_position",
            "reconcile_internal_with_broker_position",
            "update_broker_reconciliation_state",
        ),
        {
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
            "CURRENT_BROKER_ACCOUNT_ID": broker_account_id,
            "CURRENT_BROKER_POSITION_AVAILABLE": broker_position_available,
            "CURRENT_BROKER_POSITION_REASON": broker_position_reason,
            "CURRENT_POSITION_RECONCILIATION_OK": reconciliation_ok,
            "CURRENT_POSITION_RECONCILIATION_ACTION": reconciliation_action,
            "CURRENT_POSITION_RECONCILIATION_REASON": reconciliation_reason,
        },
        "update_broker_reconciliation_state",
    )


def load_refresh_broker_reconciliation(
    *,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
    broker_account_id: str | None,
    broker_position_available: bool,
    broker_position_reason: str,
    reconciliation_ok: bool,
    reconciliation_action: str,
    reconciliation_reason: str,
    lookup_account_id: str | None,
    lookup_account_reason: str,
    lookup_position_result: dict[str, Any],
) -> IsolatedBrokerRefresh:
    """Carga refresh legacy con ambas consultas sustituidas por un fake."""
    lookup = DeterministicBrokerLookup(
        lookup_account_id,
        lookup_account_reason,
        lookup_position_result,
    )
    isolated = _extract_allowed_functions(
        (
            "compare_internal_vs_broker_position",
            "normalize_tradestation_es_position",
            "reconcile_internal_with_broker_position",
            "refresh_broker_reconciliation",
            "update_broker_reconciliation_state",
        ),
        {
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
            "CURRENT_BROKER_ACCOUNT_ID": broker_account_id,
            "CURRENT_BROKER_POSITION_AVAILABLE": broker_position_available,
            "CURRENT_BROKER_POSITION_REASON": broker_position_reason,
            "CURRENT_POSITION_RECONCILIATION_OK": reconciliation_ok,
            "CURRENT_POSITION_RECONCILIATION_ACTION": reconciliation_action,
            "CURRENT_POSITION_RECONCILIATION_REASON": reconciliation_reason,
            "get_primary_tradestation_account_id": lookup.get_primary_account_id,
            "get_tradestation_es_position": lookup.get_es_position,
        },
        "refresh_broker_reconciliation",
    )
    return IsolatedBrokerRefresh(
        isolated.function,
        isolated.namespace,
        isolated.transport,
        lookup,
    )


def _load_broker_lookup_with_fake_transport(
    *,
    exposed_function: str,
    function_names: tuple[str, ...],
    response_status: int,
    response_text: str,
    response_json: Any,
    invalid_json: bool,
    transport_error: bool,
    symbol: str,
) -> IsolatedBrokerLookup:
    response = SyntheticHTTPResponse(
        response_status,
        response_text,
        response_json,
        invalid_json,
    )
    transport = DeterministicHTTPTransport(response, transport_error)
    isolated = _extract_allowed_functions(
        function_names,
        {
            "ORDER_EXECUTION_ENVIRONMENT": "SIM",
            "TS_API_BASE_URL": "https://synthetic-live.invalid",
            "TS_SIM_API_BASE_URL": "https://synthetic-sim.invalid",
            "CURRENT_EXECUTION_SYMBOL": symbol,
            "requests": SyntheticRequests,
            "tradestation_request": transport,
        },
        exposed_function,
    )
    return IsolatedBrokerLookup(
        isolated.function,
        isolated.namespace,
        transport,
    )


def load_primary_tradestation_account_id_with_fake_transport(
    *,
    response_status: int = 200,
    response_text: str = "SYNTHETIC RESPONSE",
    response_json: Any = None,
    invalid_json: bool = False,
    transport_error: bool = False,
) -> IsolatedBrokerLookup:
    """Carga el lookup de cuenta exacto sin ejecutar ningún transporte real."""
    return _load_broker_lookup_with_fake_transport(
        exposed_function="get_primary_tradestation_account_id",
        function_names=(
            "get_primary_tradestation_account_id",
            "get_tradestation_accounts",
            "get_tradestation_api_base_url",
        ),
        response_status=response_status,
        response_text=response_text,
        response_json={} if response_json is None else response_json,
        invalid_json=invalid_json,
        transport_error=transport_error,
        symbol="SYNTHETIC-ES",
    )


def load_tradestation_es_position_with_fake_transport(
    *,
    response_status: int = 200,
    response_text: str = "SYNTHETIC RESPONSE",
    response_json: Any = None,
    invalid_json: bool = False,
    transport_error: bool = False,
    symbol: str = "SYNTHETIC-ES",
) -> IsolatedBrokerLookup:
    """Carga el lookup de posición ES exacto sin transporte real."""
    return _load_broker_lookup_with_fake_transport(
        exposed_function="get_tradestation_es_position",
        function_names=(
            "get_tradestation_api_base_url",
            "get_tradestation_es_position",
            "get_tradestation_positions",
        ),
        response_status=response_status,
        response_text=response_text,
        response_json={} if response_json is None else response_json,
        invalid_json=invalid_json,
        transport_error=transport_error,
        symbol=symbol,
    )


def load_validate_position_state(
    *,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
) -> IsolatedLegacyFunction:
    """Carga el validador de posición con estado exclusivamente sintético."""
    return _extract_allowed_functions(
        ("validate_position_state",),
        {
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
        },
        "validate_position_state",
    )


def load_build_execution_intent(
    *,
    confirmed_signal: str,
    entry_execution_permission: bool,
    exit_execution_permission: bool,
    position_size_contracts: int,
    symbol: str,
) -> IsolatedLegacyFunction:
    """Carga el constructor de intención con permisos y señal sintéticos."""
    return _extract_allowed_functions(
        ("build_execution_intent",),
        {
            "CURRENT_CONFIRMED_SIGNAL": confirmed_signal,
            "CURRENT_ENTRY_EXECUTION_PERMISSION": entry_execution_permission,
            "CURRENT_EXIT_EXECUTION_PERMISSION": exit_execution_permission,
            "CURRENT_POSITION_SIZE_CONTRACTS": position_size_contracts,
            "TRADESTATION_ES_CONTRACT_SYMBOL": symbol,
        },
        "build_execution_intent",
    )


def load_execution_safety_check(
    *,
    execution_mode: str,
    live_order_execution_enabled: bool,
    position_reconciliation_ok: bool,
    execution_status: str,
    execution_action: str,
    execution_side: str,
    execution_quantity: int,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
) -> IsolatedLegacyFunction:
    """Carga safety y su validador real con estado exclusivamente sintético."""
    return _extract_allowed_functions(
        (
            "execution_safety_check",
            "validate_position_state",
        ),
        {
            "EXECUTION_MODE": execution_mode,
            "LIVE_ORDER_EXECUTION_ENABLED": live_order_execution_enabled,
            "CURRENT_POSITION_RECONCILIATION_OK": position_reconciliation_ok,
            "CURRENT_EXECUTION_STATUS": execution_status,
            "CURRENT_EXECUTION_ACTION": execution_action,
            "CURRENT_EXECUTION_SIDE": execution_side,
            "CURRENT_EXECUTION_QUANTITY": execution_quantity,
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
        },
        "execution_safety_check",
    )


def load_dispatch_execution_category_a(
    *,
    execution_status: str,
    execution_action: str,
    execution_side: str,
    execution_quantity: int,
    execution_symbol: str,
    execution_order_type: str,
    execution_reason: str,
    broker_order_state: str,
    position_state: str,
    position_contracts: int,
    position_entry_side: str,
    execution_mode: str,
    live_order_execution_enabled: bool,
    position_reconciliation_ok: bool,
    last_dispatch_signature: tuple[object, ...] | None,
    pending_order_action: str,
    pending_order_side: str,
    pending_order_quantity: int,
    pending_order_symbol: str | None,
    pending_order_submitted_at: str | None,
    broker_account_id: str | None,
) -> IsolatedCategoryADispatch:
    """Carga dispatch solo con dependencias exactas y barreras categoría A.

    La definición real de ``submit_tradestation_order`` se excluye siempre. El
    reloj también falla de forma explícita: alcanzarlo implicaría que una rama
    dejó de pertenecer a categoría A.
    """
    forbidden_submit = ForbiddenSubmit()
    forbidden_clock = ForbiddenClock()
    isolated = _extract_allowed_functions(
        (
            "build_tradestation_order_payload",
            "dispatch_execution",
            "execution_safety_check",
            "validate_position_state",
            "validate_tradestation_order_payload",
        ),
        {
            "CURRENT_EXECUTION_STATUS": execution_status,
            "CURRENT_EXECUTION_ACTION": execution_action,
            "CURRENT_EXECUTION_SIDE": execution_side,
            "CURRENT_EXECUTION_QUANTITY": execution_quantity,
            "CURRENT_EXECUTION_SYMBOL": execution_symbol,
            "CURRENT_EXECUTION_ORDER_TYPE": execution_order_type,
            "CURRENT_EXECUTION_REASON": execution_reason,
            "CURRENT_BROKER_ORDER_STATE": broker_order_state,
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_POSITION_ENTRY_SIDE": position_entry_side,
            "EXECUTION_MODE": execution_mode,
            "LIVE_ORDER_EXECUTION_ENABLED": live_order_execution_enabled,
            "CURRENT_POSITION_RECONCILIATION_OK": position_reconciliation_ok,
            "LAST_DISPATCH_SIGNATURE": last_dispatch_signature,
            "CURRENT_PENDING_ORDER_ACTION": pending_order_action,
            "CURRENT_PENDING_ORDER_SIDE": pending_order_side,
            "CURRENT_PENDING_ORDER_QUANTITY": pending_order_quantity,
            "CURRENT_PENDING_ORDER_SYMBOL": pending_order_symbol,
            "CURRENT_PENDING_ORDER_SUBMITTED_AT": pending_order_submitted_at,
            "CURRENT_BROKER_ACCOUNT_ID": broker_account_id,
            "submit_tradestation_order": forbidden_submit,
            "datetime": forbidden_clock,
            "MARKET_TZ": "SYNTHETIC-MARKET-TZ",
        },
        "dispatch_execution",
    )
    return IsolatedCategoryADispatch(
        function=isolated.function,
        namespace=isolated.namespace,
        transport=isolated.transport,
        submit=forbidden_submit,
        clock=forbidden_clock,
    )


def load_dispatch_execution_category_b_failure() -> IsolatedCategoryBFailureDispatch:
    """Carga el único escenario B autorizado: ENTRY BUY con fallo sintético.

    No extrae el submit real. ``RecordingSubmit`` y ``FixedClock`` son objetos
    nuevos por carga y no tienen dependencias externas.
    """
    recording_submit = RecordingSubmit()
    fixed_clock = FixedClock()
    isolated = _extract_allowed_functions(
        (
            "build_tradestation_order_payload",
            "dispatch_execution",
            "execution_safety_check",
            "validate_position_state",
            "validate_tradestation_order_payload",
        ),
        {
            "CURRENT_EXECUTION_STATUS": "READY",
            "CURRENT_EXECUTION_ACTION": "ENTRY",
            "CURRENT_EXECUTION_SIDE": "BUY",
            "CURRENT_EXECUTION_QUANTITY": 2,
            "CURRENT_EXECUTION_SYMBOL": "SYNTHETIC-ES",
            "CURRENT_EXECUTION_ORDER_TYPE": "MARKET",
            "CURRENT_EXECUTION_REASON": "LONG MEAN REVERSION",
            "CURRENT_BROKER_ORDER_STATE": "NONE",
            "CURRENT_POSITION_STATE": "FLAT",
            "CURRENT_POSITION_CONTRACTS": 0,
            "CURRENT_POSITION_ENTRY_SIDE": "NONE",
            "EXECUTION_MODE": "LIVE",
            "LIVE_ORDER_EXECUTION_ENABLED": True,
            "CURRENT_POSITION_RECONCILIATION_OK": True,
            "LAST_DISPATCH_SIGNATURE": (
                "PREVIOUS",
                "NONE",
                99,
                "PREVIOUS REASON",
            ),
            "CURRENT_PENDING_ORDER_ACTION": "SENTINEL_ACTION",
            "CURRENT_PENDING_ORDER_SIDE": "SENTINEL_SIDE",
            "CURRENT_PENDING_ORDER_QUANTITY": 91,
            "CURRENT_PENDING_ORDER_SYMBOL": "SENTINEL_SYMBOL",
            "CURRENT_PENDING_ORDER_SUBMITTED_AT": "SENTINEL_TIME",
            "CURRENT_BROKER_ACCOUNT_ID": "SYNTHETIC-ACCOUNT",
            "submit_tradestation_order": recording_submit,
            "datetime": fixed_clock,
            "MARKET_TZ": "SYNTHETIC-MARKET-TZ",
        },
        "dispatch_execution",
    )
    return IsolatedCategoryBFailureDispatch(
        function=isolated.function,
        namespace=isolated.namespace,
        transport=isolated.transport,
        submit=recording_submit,
        clock=fixed_clock,
    )


def load_dispatch_execution_category_b_success() -> IsolatedCategoryBSuccessDispatch:
    """Carga el único success autorizado: ENTRY BUY y OrderID sintético.

    La definición real de submit no se extrae. El fake y el reloj son locales,
    deterministas y nuevos para cada carga.
    """
    recording_submit = RecordingSuccessSubmit()
    fixed_clock = FixedClock()
    isolated = _extract_allowed_functions(
        (
            "build_tradestation_order_payload",
            "dispatch_execution",
            "execution_safety_check",
            "validate_position_state",
            "validate_tradestation_order_payload",
        ),
        {
            "CURRENT_EXECUTION_STATUS": "READY",
            "CURRENT_EXECUTION_ACTION": "ENTRY",
            "CURRENT_EXECUTION_SIDE": "BUY",
            "CURRENT_EXECUTION_QUANTITY": 2,
            "CURRENT_EXECUTION_SYMBOL": "SYNTHETIC-ES",
            "CURRENT_EXECUTION_ORDER_TYPE": "MARKET",
            "CURRENT_EXECUTION_REASON": "LONG MEAN REVERSION",
            "CURRENT_BROKER_ORDER_STATE": "NONE",
            "CURRENT_POSITION_STATE": "FLAT",
            "CURRENT_POSITION_CONTRACTS": 0,
            "CURRENT_POSITION_ENTRY_SIDE": "NONE",
            "EXECUTION_MODE": "LIVE",
            "LIVE_ORDER_EXECUTION_ENABLED": True,
            "CURRENT_POSITION_RECONCILIATION_OK": True,
            "LAST_DISPATCH_SIGNATURE": (
                "PREVIOUS",
                "NONE",
                99,
                "PREVIOUS REASON",
            ),
            "CURRENT_PENDING_ORDER_ACTION": "SENTINEL_ACTION",
            "CURRENT_PENDING_ORDER_SIDE": "SENTINEL_SIDE",
            "CURRENT_PENDING_ORDER_QUANTITY": 91,
            "CURRENT_PENDING_ORDER_SYMBOL": "SENTINEL_SYMBOL",
            "CURRENT_PENDING_ORDER_SUBMITTED_AT": "SENTINEL_TIME",
            "CURRENT_BROKER_ACCOUNT_ID": "SYNTHETIC-ACCOUNT",
            "submit_tradestation_order": recording_submit,
            "datetime": fixed_clock,
            "MARKET_TZ": "SYNTHETIC-MARKET-TZ",
        },
        "dispatch_execution",
    )
    return IsolatedCategoryBSuccessDispatch(
        function=isolated.function,
        namespace=isolated.namespace,
        transport=isolated.transport,
        submit=recording_submit,
        clock=fixed_clock,
    )


def load_build_tradestation_order_payload(
    *,
    execution_action: str,
    execution_side: str,
    execution_quantity: int,
    position_state: str,
    position_contracts: int,
    account_id: str,
    symbol: str,
    order_type: str = "MARKET",
) -> IsolatedLegacyFunction:
    """Carga build y validate con una intención enteramente sintética."""
    return _extract_allowed_functions(
        (
            "build_tradestation_order_payload",
            "validate_tradestation_order_payload",
        ),
        {
            "CURRENT_EXECUTION_ACTION": execution_action,
            "CURRENT_EXECUTION_SIDE": execution_side,
            "CURRENT_EXECUTION_QUANTITY": execution_quantity,
            "CURRENT_POSITION_STATE": position_state,
            "CURRENT_POSITION_CONTRACTS": position_contracts,
            "CURRENT_BROKER_ACCOUNT_ID": account_id,
            "CURRENT_EXECUTION_SYMBOL": symbol,
            "CURRENT_EXECUTION_ORDER_TYPE": order_type,
        },
        "build_tradestation_order_payload",
    )


def load_get_tradestation_api_base_url(
    *,
    order_execution_environment: str,
    live_api_base_url: str,
    sim_api_base_url: str,
) -> IsolatedLegacyFunction:
    """Carga el selector con endpoints sintéticos que son solo strings."""
    return _extract_allowed_functions(
        ("get_tradestation_api_base_url",),
        {
            "ORDER_EXECUTION_ENVIRONMENT": order_execution_environment,
            "TS_API_BASE_URL": live_api_base_url,
            "TS_SIM_API_BASE_URL": sim_api_base_url,
        },
        "get_tradestation_api_base_url",
    )


def load_submit_tradestation_order(
    *,
    live_order_execution_enabled: bool = False,
    order_execution_environment: str = "SIM",
) -> IsolatedLegacyFunction:
    """Carga submit y su validador exacto en un namespace desechable.

    La función del baseline no se modifica. Cada llamada crea un namespace y
    un sentinel nuevos, de modo que los cambios sintéticos de un test no pueden
    contaminar otro test ni el archivo original.
    """
    return _extract_allowed_functions(
        (
            "validate_tradestation_order_payload",
            "submit_tradestation_order",
        ),
        {
            "LIVE_ORDER_EXECUTION_ENABLED": live_order_execution_enabled,
            "ORDER_EXECUTION_ENVIRONMENT": order_execution_environment,
        },
        "submit_tradestation_order",
    )
