import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

PATH = Path(__file__).parents[1] / "tools" / "thetadata_entitlement_probe.py"
WRAPPER = PATH.with_name("run_thetadata_entitlement_probe.ps1")
SPEC = importlib.util.spec_from_file_location("entitlement_probe", PATH)
probe = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)
DAY = date(2026, 1, 15)
NOW = lambda: datetime(2026, 1, 16, tzinfo=timezone.utc)


def contract_payload():
    return {"data": [{"root": "SPXW", "expiration": "20260115", "strike": 6000000, "right": "C"}]}


def available_transport(path, params, key):
    if path.endswith("contracts"): return 200, contract_payload()
    return 200, {"data": [{"price": 1, "size": 1, "rate": 1, "gamma": 1, "iv": 1, "delta": 1, "bid": 1, "ask": 1, "open_interest": 1, "subscription": "x"}]}


def run(transport=available_transport):
    return probe.run(DAY, dry_run=False, transport=transport, environ={"THETADATA_API_KEY": "synthetic-secret"}, now=NOW)


def test_exactly_nine_fixed_probes_and_no_tenth():
    assert probe.MAX_LOGICAL_PROBES == len(probe.PROBES) == 9
    assert [p.probe_id for p in probe.PROBES] == [f"P{i}" for i in range(1, 10)]


@pytest.mark.parametrize("bad", ["2026-01-01,2026-01-02", "2026-01-01..2026-01-02", "20260101", "today"])
def test_cli_rejects_ranges_and_requires_single_iso_date(bad):
    with pytest.raises(SystemExit): probe.build_parser().parse_args(["--date", bad])


def test_missing_credential_fails_closed_before_transport():
    called = []
    with pytest.raises(RuntimeError, match="^CREDENTIAL_UNAVAILABLE$"):
        probe.run(DAY, dry_run=False, transport=lambda *a: called.append(a), environ={})
    assert called == []


def test_dry_run_reads_no_credential_and_makes_no_calls():
    class Exploding(dict):
        def get(self, *args): raise AssertionError("credential read")
    result = probe.run(DAY, dry_run=True, transport=lambda *a: pytest.fail("network"), environ=Exploding(), now=NOW)
    assert result["safety_ledger"]["credential_reads"] == 0
    assert result["safety_ledger"]["authenticated_calls"] == 0
    assert result["safety_ledger"]["provider_data_calls"] == 0


def test_plan_is_get_only_allowlisted_and_has_no_pagination():
    source = PATH.read_text()
    assert 'method="GET"' in source
    assert not any(word in [p.path.lower() for p in probe.PROBES] for word in ("order", "bulk"))
    assert "next_page" not in source and "page_size" not in source
    assert probe.MUTATION_METHODS == {"POST", "PUT", "PATCH", "DELETE"}


def test_contract_selection_is_deterministic_and_observed():
    payload = {"data": [
        {"root":"SPXW", "expiration":"20260115", "strike":6100000, "right":"P"},
        {"root":"SPXW", "expiration":"20260115", "strike":6000000, "right":"C"},
        {"root":"SPXW", "expiration":"20260116", "strike":1, "right":"C"},]}
    assert probe.select_contract(payload, DAY)["strike"] == 6000000
    assert probe.select_contract({"data": []}, DAY) is None


def test_p2_failure_blocks_only_contract_dependents_not_index():
    calls = []
    def transport(path, params, key):
        calls.append(path)
        return (200, {"data": []}) if path.endswith("contracts") else available_transport(path, params, key)
    result = run(transport)
    by_id = {x["probe_id"]: x for x in result["probe_results"]}
    assert all(by_id[f"P{i}"]["outcome"] == "NOT_TESTED" for i in range(3, 8))
    assert by_id["P8"]["outcome"] == "VERIFIED_AVAILABLE"
    assert not any(f"/option/history/" in p for p in calls)


def test_options_do_not_infer_indices_and_p6_does_not_infer_gamma():
    def transport(path, params, key):
        if path.endswith("contracts"): return 200, contract_payload()
        if path == "/index/history/price": return 200, {"data": []}
        if path == "/option/history/eod": return 402, {}
        return available_transport(path, params, key)
    by_id = {x["probe_id"]: x for x in run(transport)["probe_results"]}
    assert by_id["P6"]["outcome"] == "VERIFIED_AVAILABLE"
    assert by_id["P7"]["outcome"] == "VERIFIED_DENIED"
    assert by_id["P8"]["outcome"] == "AMBIGUOUS"


@pytest.mark.parametrize("behavior,expected,status", [
    (lambda: (200, {"data": []}), "AMBIGUOUS", "EMPTY_SUCCESS"),
    (lambda: (401, {}), "AMBIGUOUS", "AUTH_OR_ACCESS_ERROR"),
])
def test_empty_and_auth_are_not_denied(behavior, expected, status):
    def transport(path, params, key):
        if path.endswith("contracts"): return 200, contract_payload()
        if path.endswith("quote"): return behavior()
        return available_transport(path, params, key)
    item = run(transport)["probe_results"][2]
    assert (item["outcome"], item["status_class"]) == (expected, status)


def test_timeout_is_not_denied_and_secret_is_redacted():
    secret = "SYNTHETIC-DO-NOT-LEAK"
    def transport(path, params, key):
        if path.endswith("contracts"): return 200, contract_payload()
        if path.endswith("quote"): raise TimeoutError(secret)
        return available_transport(path, params, key)
    encoded = json.dumps(probe.run(DAY, dry_run=False, transport=transport, environ={"THETADATA_API_KEY": secret}, now=NOW))
    assert secret not in encoded
    assert '"outcome": "AMBIGUOUS"' in encoded and '"status_class": "TIMEOUT"' in encoded


@pytest.mark.parametrize("payload", ["malformed", {"data": [{"unexpected": 123}]}, {"data": [{"bid": 1}]}])
def test_malformed_or_partial_schema_is_not_verified(payload):
    def transport(path, params, key):
        if path.endswith("contracts"): return 200, contract_payload()
        if path.endswith("quote"): return 200, payload
        return available_transport(path, params, key)
    item = run(transport)["probe_results"][2]
    assert item["outcome"] in {"AMBIGUOUS", "ERROR"}


def test_json_has_only_sanitized_shape_and_no_market_values(tmp_path):
    result = run()
    output = tmp_path / "result.json"
    probe.write_result(result, output)
    data = json.loads(output.read_text())
    assert set(data) == {"schema_version", "execution_id", "verification_time", "requested_date", "probe_results", "safety_ledger"}
    forbidden = {"headers", "cookies", "raw_response", "market_rows", "api_key"}
    assert not forbidden.intersection(json.dumps(data).lower())
    assert data["safety_ledger"]["raw_payloads_persisted"] == 0


def test_ledger_invariants_max_nine_and_cutover_no():
    ledger = run()["safety_ledger"]
    probe.assert_safety(ledger)
    assert ledger["probes_attempted"] <= 9 and ledger["credential_reads"] <= 1
    assert ledger["cutover"] == "NO"
    for key in ("POST", "PUT", "PATCH", "DELETE", "runtime_modifications", "mapping_promotions"):
        assert ledger[key] == 0


def test_deterministic_plan_and_outcomes_except_nonsensitive_execution_id():
    first, second = run(), run()
    assert first["probe_results"] == second["probe_results"]
    assert first["safety_ledger"] == second["safety_ledger"]


def test_causal_mapping_is_neither_read_nor_written():
    source = PATH.read_text().lower()
    assert "causal_greeks_inputs" not in source
    assert "causal_mapping_status_snapshot" not in source


def test_powershell_wrapper_is_fail_closed_and_never_echoes_key():
    source = WRAPPER.read_text()
    assert "CREDENTIAL_UNAVAILABLE" in source
    assert "SANITIZED_RESULT_NOT_GENERATED" in source
    assert "THETADATA_API_KEY" in source
    assert "Write-Output" not in source and "Write-Host" not in source
    assert "--dry-run" not in source  # authenticated human wrapper cannot weaken itself
