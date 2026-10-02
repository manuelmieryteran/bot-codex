import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "docs/evidence/phase5c4b4c2_thetadata_account"
SOURCE = EVIDENCE_DIR / "probe_result_v2.json"
SUMMARY_PATH = EVIDENCE_DIR / "evidence_summary.json"
CHECKPOINT = EVIDENCE_DIR / "review_checkpoint.md"
SOURCE_SHA256 = "af908e2213baa028ac7a501483221a00cb50305aef59ecce044c9bd466dc00a0"


def load_json(path):
    return json.loads(path.read_bytes())


def probes_by_id():
    return {row["probe_id"]: row for row in load_json(SOURCE)["probe_results"]}


def test_source_is_immutable_valid_and_has_exact_probe_set():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    source = load_json(SOURCE)
    assert source["schema_version"] == "1.0"
    assert source["requested_date"] == "2026-01-15"
    ids = [row["probe_id"] for row in source["probe_results"]]
    assert ids == [f"P{number}" for number in range(1, 10)]
    assert len(ids) == len(set(ids)) == 9
    assert "P10" not in ids


def test_outcomes_are_derived_as_seven_zero_one_zero_one():
    counts = Counter(row["outcome"] for row in load_json(SOURCE)["probe_results"])
    expected = {
        "VERIFIED_AVAILABLE": 7,
        "VERIFIED_DENIED": 0,
        "AMBIGUOUS": 1,
        "NOT_TESTED": 0,
        "ERROR": 1,
    }
    assert {key: counts[key] for key in expected} == expected
    assert load_json(SUMMARY_PATH)["outcome_counts"] == expected


def test_safety_ledger_is_exact():
    expected = {
        "credential_reads": 1, "authenticated_calls": 9, "technical_retries": 0,
        "provider_data_calls": 8, "probes_attempted": 9, "probes_available": 7,
        "probes_denied": 0, "probes_ambiguous": 1, "probes_not_tested": 0,
        "probes_error": 1, "rows_observed": 17334, "raw_payloads_persisted": 0,
        "POST": 0, "PUT": 0, "PATCH": 0, "DELETE": 0, "orders": 0,
        "TradeStation": 0, "DigitalOcean": 0, "backtests": 0,
        "runtime_modifications": 0, "mapping_promotions": 0, "cutover": "NO",
    }
    assert load_json(SOURCE)["safety_ledger"] == expected
    assert load_json(SUMMARY_PATH)["safety_ledger"] == expected


def test_p2_scope_anomaly_and_single_date_limit_are_frozen():
    p2 = probes_by_id()["P2"]
    summary = load_json(SUMMARY_PATH)
    anomaly, = summary["scope_anomalies"]
    assert p2["row_count"] == 17326
    assert p2["schema_verified"] is True
    assert anomaly["probe_id"] == "P2"
    assert anomaly["classification"] == "ACQUISITION_SCOPE_ANOMALY"
    assert anomaly["rows_observed_transiently"] == 17326
    assert anomaly["market_or_contract_values_persisted"] is False
    assert anomaly["automatic_repeat_permitted"] is False
    assert summary["historical_depth_status"][p2["capability"]] == "SINGLE_DATE_ONLY"


def test_account_metadata_does_not_infer_tier_or_indices():
    metadata = load_json(SUMMARY_PATH)["account_metadata_interpretation"]
    assert metadata == {
        "ACCOUNT_METADATA_ACCESS": "VERIFIED_AVAILABLE",
        "ACCOUNT_TIER_INTERPRETATION": "UNRESOLVED",
        "ACCOUNT_TIER_VALUE": "NOT_PERSISTED",
        "fields_observed": ["index_subscription", "options_subscription"],
        "options_implies_indices": False,
    }


def test_quote_and_open_interest_acquisition_do_not_promote_mappings():
    summary = load_json(SUMMARY_PATH)
    assert summary["acquisition_capabilities"]["OPTION_QUOTE_ACQUISITION"] == "VERIFIED_AVAILABLE"
    assert summary["acquisition_capabilities"]["OPEN_INTEREST_ACQUISITION"] == "VERIFIED_AVAILABLE"
    assert summary["causal_mapping_snapshot"]["quotes"] == "BLOCKED_UNRESOLVED"
    assert summary["causal_mapping_snapshot"]["OI"] == "BLOCKED_UNRESOLVED"


def test_trade_result_stays_ambiguous_empty_success():
    p4 = probes_by_id()["P4"]
    unresolved = load_json(SUMMARY_PATH)["unresolved_capabilities"]["OPTION_TRADE_ENTITLEMENT"]
    assert (p4["outcome"], p4["status_class"], p4["row_count"]) == ("AMBIGUOUS", "EMPTY_SUCCESS", 0)
    assert unresolved["status"] == "AMBIGUOUS"
    assert len(unresolved["possible_causes"]) == 5


def test_p6_p7_are_available_independent_and_noncausal():
    summary = load_json(SUMMARY_PATH)
    acquisition = summary["acquisition_capabilities"]
    guards = summary["interpretation_guards"]
    assert acquisition["PROVIDER_IV_FIRST_ORDER_GREEKS_ACQUISITION"] == "VERIFIED_AVAILABLE"
    assert acquisition["EOD_GAMMA_ACQUISITION"] == "VERIFIED_AVAILABLE"
    assert summary["causal_mapping_snapshot"]["provider_greeks_iv"] == "EXCLUDED"
    assert summary["causal_mapping_snapshot"]["local_greeks_iv"] == "NEEDS_RECONSTRUCTION"
    assert guards["P6_and_P7_independent"] is True
    assert guards["EOD_gamma_implies_intraday_gamma"] is False


def test_spx_error_stays_unresolved_and_options_do_not_imply_indices():
    p8 = probes_by_id()["P8"]
    summary = load_json(SUMMARY_PATH)
    unresolved = summary["unresolved_capabilities"]["SPX_INDEX_HISTORY_ENTITLEMENT"]
    assert (p8["outcome"], p8["status_class"]) == ("ERROR", "TRANSPORT_ERROR")
    assert unresolved["status"] == "UNRESOLVED"
    assert summary["account_metadata_interpretation"]["options_implies_indices"] is False
    assert summary["causal_mapping_snapshot"]["SPX"] == "BLOCKED_UNRESOLVED"


def test_rate_acquisition_does_not_infer_causal_availability():
    summary = load_json(SUMMARY_PATH)
    assert summary["acquisition_capabilities"]["INTEREST_RATE_HISTORY_ACQUISITION"] == "VERIFIED_AVAILABLE"
    assert summary["interpretation_guards"]["retrospective_rate_implies_intraday_availability"] is False
    assert summary["unresolved_capabilities"]["causal_rate_availability"] == "NOT_INFERRED"


def test_all_historical_depth_is_single_date_only():
    summary = load_json(SUMMARY_PATH)
    assert len(summary["historical_depth_status"]) == 9
    assert set(summary["historical_depth_status"].values()) == {"SINGLE_DATE_ONLY"}
    assert summary["interpretation_guards"]["single_date_implies_general_historical_depth"] is False


def test_exact_causal_snapshot_zero_promotions_and_no_cutover():
    summary = load_json(SUMMARY_PATH)
    assert summary["causal_mapping_snapshot"] == {
        "provider_greeks_iv": "EXCLUDED", "local_greeks_iv": "NEEDS_RECONSTRUCTION",
        "SPX": "BLOCKED_UNRESOLVED", "OI": "BLOCKED_UNRESOLVED",
        "trades": "BLOCKED_UNRESOLVED", "quotes": "BLOCKED_UNRESOLVED",
        "historical_SPXW_0DTE_universe": {
            "status": "READY_WITH_CONSERVATIVE_RULE", "confidence": "LOW"
        },
    }
    assert summary["mapping_promotions"] == 0
    assert summary["cutover"] == "NO"


def test_summary_is_canonical_deterministic_json_and_references_source_hash():
    raw = SUMMARY_PATH.read_text(encoding="utf-8")
    summary = json.loads(raw)
    assert raw == json.dumps(summary, indent=2, sort_keys=True) + "\n"
    assert summary["source_file"] == SOURCE.name
    assert summary["source_sha256"] == SOURCE_SHA256
    assert summary["probe_count"] == 9


def test_new_artifacts_have_no_secret_material():
    # Match secret-bearing syntax, not legitimate prose or metric names such as
    # credential_reads, access token discussions, or the word "passwords".
    patterns = [
        rb"(?i)authorization\s*:\s*bearer\s+\S+",
        rb"(?i)(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|cookie)\s*[=:]\s*['\"]?[^\s,'\"}]{8,}",
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    for path in (SOURCE, SUMMARY_PATH, CHECKPOINT, Path(__file__)):
        payload = path.read_bytes()
        assert not any(re.search(pattern, payload) for pattern in patterns), path


def test_protected_runtime_and_evidence_files_are_unchanged():
    protected = {
        "spx_data_FASE4_ESTABLE_FINAL_CANDIDATO.py": "84b66fd5f60cbc1623fb950d1340bd314bb75f8f09db40271cc9868590ae4023",
        "spx_data_FASE5.py": "5527f41cd20f5e383ba0957c26a4bd250037c0b2502a3b047797799b1102aed6",
        "src/bot_spx/historical.py": "da55312f1f00520a15c6495ec999fd8cd9425e52387168b42905c3b8bfc0684e",
        "src/bot_spx/historical_provider_spec.py": "6786c6b31d0d5491232c227225f46cf0ed1b8c22fb1c08085dff06e2ba9445dd",
        "src/bot_spx/local_greeks.py": "3227f8fae6257b09fa2c4b1a99b2622be3f481a498ae4e6d70aa8cc6a9d85b1d",
        "src/bot_spx/causal_greeks_inputs.py": "e70378ffeaa58bcae5b1de2436b14a46cb72a3fcef049fc41baa2a164a8d0017",
        "src/bot_spx/account_entitlement.py": "dca8834d855b226debe208c45c46159bf7f1e07a475e1a02a21425904134669c",
        "tools/thetadata_entitlement_probe.py": "b16c6abd0b4d92490fcc2553b58e04bb605d4c3ee7afd30b7c1f6c305e528bae",
        "tools/run_thetadata_entitlement_probe.ps1": "3ef94098dd2688866dd5f24ed91a8937852cde777d2c4bde8b3072d1de8ed95f",
        "docs/evidence/phase5c4b2_thetadata/raw_response.md": "12d56f13a04f94deb6c74dc53fe16d8f888f4a3ecc2a2fdda81c74d49157728d",
        "docs/evidence/phase5c4b2_thetadata/evidence_ledger.json": "ac1365e2848a3f9e587e0795b5d887e8c9829bb7fe81e5038d876418aac8c069",
        "docs/evidence/phase5c4b3_human_mapping_decision.md": "653d138f3327deda78a478e3f61e05e073af63f797481fe68dc712c292575925",
    }
    actual = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in protected}
    assert actual == protected
