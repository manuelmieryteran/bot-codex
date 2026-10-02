#!/usr/bin/env python3
"""Nine-query, read-only ThetaData entitlement probe.

This deliberately small utility is isolated from the trading runtime.  Real use is
manual only; tests inject a transport and never contact ThetaData.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

MAX_LOGICAL_PROBES = 9
OUTPUT_NAME = "phase5c4b4c2_probe_result.json"
BASE_URL = "https://api.thetadata.us/v3"
OUTCOMES = frozenset({"VERIFIED_AVAILABLE", "VERIFIED_DENIED", "AMBIGUOUS", "NOT_TESTED", "ERROR"})
MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class Probe:
    probe_id: str
    capability: str
    endpoint_family: str
    path: str
    expected_any: tuple[str, ...]
    dependent_on_contract: bool = False


PROBES = (
    Probe("P1", "ACCOUNT_METADATA", "account", "/account/subscription", ("subscription",)),
    Probe("P2", "SPX_SPXW_CONTRACT_LIST", "option_contract", "/option/list/contracts", ("root", "expiration", "strike", "right")),
    Probe("P3", "OPTION_QUOTE", "option_quote", "/option/history/quote", ("bid", "ask"), True),
    Probe("P4", "OPTION_TRADE", "option_trade", "/option/history/trade", ("price", "size"), True),
    Probe("P5", "OPEN_INTEREST", "option_open_interest", "/option/history/open_interest", ("open_interest",), True),
    Probe("P6", "IV_FIRST_ORDER_GREEKS", "option_greeks_first_order", "/option/history/greeks/first_order", ("iv", "delta"), True),
    Probe("P7", "EOD_GAMMA", "option_eod", "/option/history/eod", ("gamma",), True),
    Probe("P8", "SPX_INDEX_HISTORY", "index_price", "/index/history/price", ("price",)),
    Probe("P9", "INTEREST_RATE_HISTORY", "interest_rate", "/interest_rate/history/eod", ("rate",)),
)


def parse_date(value: str) -> date:
    if any(mark in value for mark in (",", "/", "..", ":")):
        raise argparse.ArgumentTypeError("one ISO date is required; ranges are prohibited")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
    if value != parsed.isoformat():
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fixed nine-probe ThetaData entitlement audit")
    parser.add_argument("--date", required=True, type=parse_date, dest="requested_date")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(OUTPUT_NAME))
    return parser


def new_ledger() -> dict[str, Any]:
    return {
        "credential_reads": 0, "authenticated_calls": 0, "technical_retries": 0,
        "provider_data_calls": 0, "probes_attempted": 0, "probes_available": 0,
        "probes_denied": 0, "probes_ambiguous": 0, "probes_not_tested": 0,
        "probes_error": 0, "rows_observed": 0, "raw_payloads_persisted": 0,
        "POST": 0, "PUT": 0, "PATCH": 0, "DELETE": 0, "orders": 0,
        "TradeStation": 0, "DigitalOcean": 0, "backtests": 0,
        "runtime_modifications": 0, "mapping_promotions": 0, "cutover": "NO",
    }


def assert_safety(ledger: Mapping[str, Any]) -> None:
    if len(PROBES) != MAX_LOGICAL_PROBES or [p.probe_id for p in PROBES] != [f"P{i}" for i in range(1, 10)]:
        raise RuntimeError("INVALID_PROBE_PLAN")
    if ledger["credential_reads"] > 1 or ledger["probes_attempted"] > MAX_LOGICAL_PROBES:
        raise RuntimeError("SAFETY_LIMIT_EXCEEDED")
    for key in (*MUTATION_METHODS, "orders", "TradeStation", "DigitalOcean", "backtests", "runtime_modifications", "mapping_promotions", "raw_payloads_persisted"):
        if ledger[key] != 0:
            raise RuntimeError("SAFETY_INVARIANT_FAILED")
    if ledger["cutover"] != "NO":
        raise RuntimeError("SAFETY_INVARIANT_FAILED")


def _params(probe: Probe, day: date, contract: Mapping[str, Any] | None) -> dict[str, str]:
    d = day.strftime("%Y%m%d")
    if probe.probe_id == "P1": return {}
    if probe.probe_id == "P2": return {"root": "SPXW", "expiration": d}
    if probe.probe_id == "P8": return {"root": "SPX", "start_date": d, "end_date": d, "interval": "1m"}
    if probe.probe_id == "P9": return {"date": d}
    assert contract is not None
    result = {k: str(contract[k]) for k in ("root", "expiration", "strike", "right")}
    if probe.probe_id in {"P3", "P4", "P6"}: result.update({"start_date": d, "end_date": d, "interval": "1m"})
    else: result["date"] = d
    return result


def select_contract(payload: Any, day: date) -> dict[str, Any] | None:
    """Choose one observed same-day SPXW contract, deterministically."""
    rows = extract_rows(payload)
    wanted = day.strftime("%Y%m%d")
    candidates = []
    for row in rows:
        if not isinstance(row, Mapping): continue
        normalized = {str(k).lower(): v for k, v in row.items()}
        if str(normalized.get("root", "")).upper() != "SPXW": continue
        expiration = str(normalized.get("expiration", "")).replace("-", "")
        if expiration != wanted: continue
        if all(normalized.get(k) is not None for k in ("strike", "right")):
            candidates.append({"root": "SPXW", "expiration": expiration, "strike": normalized["strike"], "right": str(normalized["right"]).upper()})
    if not candidates: return None
    return sorted(candidates, key=lambda c: (str(c["strike"]), str(c["right"])))[0]


def extract_rows(payload: Any) -> list[Any]:
    if isinstance(payload, list): return payload
    if not isinstance(payload, Mapping): return []
    for key in ("data", "response", "contracts", "results"):
        value = payload.get(key)
        if isinstance(value, list): return value
        if isinstance(value, Mapping): return [value]
    return [payload] if payload else []


def _field_names(rows: Sequence[Any]) -> list[str]:
    names: set[str] = set()
    for row in rows:
        if isinstance(row, Mapping): names.update(str(k).lower() for k in row)
    # Names only: never values. Restrict to simple identifiers defensively.
    return sorted(n for n in names if n.replace("_", "").isalnum())[:64]


def sanitize_error(exc: BaseException) -> str:
    """Return only an allow-listed class; exception text is never retained."""
    if isinstance(exc, TimeoutError): return "TIMEOUT"
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in (401, 403): return "AUTH_OR_ACCESS_ERROR"
        return "HTTP_ERROR"
    if isinstance(exc, (ValueError, TypeError, json.JSONDecodeError)): return "MALFORMED_RESPONSE"
    return "TRANSPORT_ERROR"


def _result(probe: Probe, day: date, outcome: str, status: str, *, fields: Sequence[str] = (), rows: int = 0, schema: bool = False, ambiguity: str = "NONE", note: str = "") -> dict[str, Any]:
    if outcome not in OUTCOMES: raise ValueError("invalid outcome")
    return {"probe_id": probe.probe_id, "capability": probe.capability, "outcome": outcome,
            "endpoint_family": probe.endpoint_family, "status_class": status,
            "fields_observed": list(fields), "resolution_observed": "MINIMUM_SINGLE_DATE",
            "row_count": rows, "date_tested": day.isoformat(), "schema_verified": schema,
            "entitlement_interpretation": outcome, "ambiguity": ambiguity, "notes": note}


Transport = Callable[[str, Mapping[str, str], str], tuple[int, Any]]


def official_rest_transport(path: str, params: Mapping[str, str], api_key: str) -> tuple[int, Any]:
    """One GET via ThetaData's documented v3 HTTPS API-key mechanism."""
    if path not in {p.path for p in PROBES}: raise RuntimeError("ENDPOINT_NOT_ALLOWLISTED")
    url = BASE_URL + path
    if params: url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read())


def run(day: date, *, dry_run: bool, transport: Transport | None = None, environ: Mapping[str, str] | None = None, now: Callable[[], datetime] | None = None) -> dict[str, Any]:
    ledger = new_ledger()
    env = os.environ if environ is None else environ
    clock = now or (lambda: datetime.now(timezone.utc))
    results: list[dict[str, Any]] = []
    contract = None
    api_key = ""
    if not dry_run:
        ledger["credential_reads"] = 1
        api_key = env.get("THETADATA_API_KEY", "")
        if not api_key:
            raise RuntimeError("CREDENTIAL_UNAVAILABLE")
    for probe in PROBES:
        if dry_run:
            results.append(_result(probe, day, "NOT_TESTED", "DRY_RUN", ambiguity="NOT_EXECUTED", note="Plan validated without credential or network access."))
            ledger["probes_not_tested"] += 1
            continue
        if probe.dependent_on_contract and contract is None:
            results.append(_result(probe, day, "NOT_TESTED", "DEPENDENCY_UNAVAILABLE", ambiguity="P2_CONTRACT_UNAVAILABLE", note="No observed eligible contract; no request made."))
            ledger["probes_not_tested"] += 1
            continue
        ledger["probes_attempted"] += 1; ledger["authenticated_calls"] += 1; ledger["provider_data_calls"] += 1
        try:
            status, payload = (transport or official_rest_transport)(probe.path, _params(probe, day, contract), api_key)
            rows = extract_rows(payload); fields = _field_names(rows); count = len(rows)
            ledger["rows_observed"] += count
            if status in (401, 403):
                outcome, status_class, schema, ambiguity = "AMBIGUOUS", "AUTH_OR_ACCESS_ERROR", False, "AUTH_FAILURE_IS_NOT_DATASET_DENIAL"
            elif status in (402, 451):
                outcome, status_class, schema, ambiguity = "VERIFIED_DENIED", "EXPLICIT_ENTITLEMENT_DENIAL", False, "NONE"
            elif not 200 <= status < 300:
                outcome, status_class, schema, ambiguity = "ERROR", "HTTP_ERROR", False, "HTTP_FAILURE"
            elif not rows:
                outcome, status_class, schema, ambiguity = "AMBIGUOUS", "EMPTY_SUCCESS", False, "EMPTY_IS_NOT_DENIAL"
            else:
                schema = all(name in fields for name in probe.expected_any)
                outcome, status_class, ambiguity = ("VERIFIED_AVAILABLE", "SUCCESS", "NONE") if schema else ("AMBIGUOUS", "SUCCESS_SCHEMA_UNVERIFIED", "MALFORMED_OR_PARTIAL_SCHEMA")
            result = _result(probe, day, outcome, status_class, fields=fields, rows=count, schema=schema, ambiguity=ambiguity)
            if probe.probe_id == "P2" and outcome == "VERIFIED_AVAILABLE": contract = select_contract(payload, day)
        except BaseException as exc:
            cls = sanitize_error(exc)
            outcome = "AMBIGUOUS" if cls in {"TIMEOUT", "AUTH_OR_ACCESS_ERROR"} else "ERROR"
            result = _result(probe, day, outcome, cls, ambiguity="NO_ENTITLEMENT_INFERENCE", note="Sanitized failure; no exception details retained.")
        results.append(result)
        ledger[{"VERIFIED_AVAILABLE":"probes_available", "VERIFIED_DENIED":"probes_denied", "AMBIGUOUS":"probes_ambiguous", "NOT_TESTED":"probes_not_tested", "ERROR":"probes_error"}[result["outcome"]]] += 1
    assert_safety(ledger)
    return {"schema_version": "1.0", "execution_id": str(uuid.uuid4()),
            "verification_time": clock().astimezone(timezone.utc).isoformat(),
            "requested_date": day.isoformat(), "probe_results": results, "safety_ledger": ledger}


def write_result(result: Mapping[str, Any], output: Path) -> None:
    assert_safety(result["safety_ledger"])
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args.requested_date, dry_run=args.dry_run)
        write_result(result, args.output)
    except RuntimeError as exc:
        # RuntimeError messages originate only from fixed internal constants.
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
