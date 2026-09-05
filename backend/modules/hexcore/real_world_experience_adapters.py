"""Real-world experience adapter portfolio for AION's learned subjects.

Every adapter binds a subject bundle to an independently owned authority.
Readiness, observation, intervention, and external-write authority are separate
gates.  An installed adapter is never evidence that its mission succeeded.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from backend.modules.hexcore.file_locking import exclusive_file_lock


SCHEMA = "aion.hexcore.real_world_experience_adapters.v1"
LEVEL = {"unassessed": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}

ADAPTERS: tuple[dict[str, Any], ...] = (
    {
        "adapter_id": "prediction_market_intelligence_v1",
        "strategic_priority": 1,
        "learning_order": [
            "probabilistic_forecasting_calibration", "event_evidence_resolution_research",
            "prediction_market_microstructure", "elections_polling_public_opinion",
            "prediction_market_design_compliance",
        ],
        "title": "Live prediction-market intelligence and delayed paper outcomes",
        "safe_early_experience": True,
        "experience_entry_subjects": {
            "probabilistic_forecasting_calibration": "beginner",
        },
        "required_subjects": {
            "probabilistic_forecasting_calibration": "advanced",
            "event_evidence_resolution_research": "advanced",
            "prediction_market_microstructure": "advanced",
            "elections_polling_public_opinion": "advanced",
            "prediction_market_design_compliance": "advanced",
        },
        "authority": "live public Polymarket and Kalshi orderbooks, frozen point-in-time forecasts, later platform settlements, independent Brier/PnL recalculation and jurisdiction checks",
        "risk": "high_stakes_prediction_market_research",
        "external_write_policy": "public read-only and paper-only; live orders require a separate owner-signed loss mandate, platform eligibility and per-order approval during qualification",
    },
    {
        "adapter_id": "owned_purple_team_security_assessment_v1",
        "strategic_priority": 1,
        "learning_order": [
            "cybersecurity", "application_web_api_security", "network_wireless_security",
            "cloud_identity_container_security", "adversary_emulation_penetration_testing",
            "exploit_analysis_reverse_engineering",
            "detection_threat_hunting_incident_response", "cryptography_protocol_security",
            "hardware_embedded_ot_security", "security_research_disclosure",
            "security_architecture_operations",
        ],
        "title": "Owned purple-team cybersecurity assessment and repair",
        "required_subjects": {
            "cybersecurity": "advanced",
            "application_web_api_security": "advanced",
            "network_wireless_security": "advanced",
            "cloud_identity_container_security": "advanced",
            "adversary_emulation_penetration_testing": "advanced",
            "exploit_analysis_reverse_engineering": "advanced",
            "detection_threat_hunting_incident_response": "advanced",
            "cryptography_protocol_security": "advanced",
            "hardware_embedded_ot_security": "advanced",
            "security_research_disclosure": "advanced",
            "security_architecture_operations": "advanced",
        },
        "authority": "signed target-and-method scope, isolated range receipt, frozen vulnerable baseline, attack/detection ledger, patched regression suite and independent retest",
        "risk": "dual_use_cybersecurity",
        "external_write_policy": "owned isolated lab or explicitly authorised scope only; fail closed outside scope",
    },
    {
        "adapter_id": "upstream_software_problem_and_repair_v1",
        "strategic_priority": 7,
        "title": "Real upstream software problem and verified private repair",
        "safe_early_experience": True,
        "experience_entry_subjects": {
            "software_engineering": "beginner", "testing_debugging": "beginner",
        },
        "required_subjects": {"software_engineering": "advanced", "testing_debugging": "advanced"},
        "authority": "GitHub CPython issue tracker plus pinned upstream repository tests",
        "risk": "bounded_private_code",
        "external_write_policy": "forbidden_without_owner_approval",
    },
    {
        "adapter_id": "tessaris_business_outcome_v1",
        "strategic_priority": 5,
        "title": "Measured Tessaris business operating outcome",
        "required_subjects": {
            "business_management": "beginner",
            "accounting_corporate_finance": "beginner",
        },
        "authority": "versioned Tessaris business containers and later owner-confirmed operating metrics",
        "risk": "business_decision",
        "external_write_policy": "proposal_only_until_owner_approval",
    },
    {
        "adapter_id": "institutional_finance_intelligence_v1",
        "strategic_priority": 4,
        "learning_order": [
            "probability_statistics", "financial_mathematics",
            "accounting_corporate_finance", "economics_core", "markets_investing",
            "stochastic_processes_finance", "financial_econometrics",
            "quantitative_research", "asset_pricing", "derivatives_structured_products",
            "portfolio_construction", "financial_risk_management",
            "market_microstructure_execution", "systematic_trading",
            "fundamental_equity_credit", "financial_regulation_compliance",
            "institutional_banking_treasury", "alternative_private_markets",
            "tax_wealth_structuring", "financial_data_infrastructure",
            "hedge_fund_operations",
        ],
        "title": "Institutional quant, investment and hedge-fund intelligence",
        "required_subjects": {
            "probability_statistics": "advanced",
            "financial_mathematics": "advanced",
            "accounting_corporate_finance": "advanced",
            "economics_core": "advanced",
            "markets_investing": "advanced",
            "stochastic_processes_finance": "intermediate",
            "financial_econometrics": "advanced",
            "quantitative_research": "advanced",
            "asset_pricing": "advanced",
            "derivatives_structured_products": "advanced",
            "portfolio_construction": "advanced",
            "financial_risk_management": "advanced",
            "market_microstructure_execution": "advanced",
            "systematic_trading": "advanced",
            "fundamental_equity_credit": "advanced",
            "financial_regulation_compliance": "intermediate",
            "institutional_banking_treasury": "advanced",
            "alternative_private_markets": "advanced",
            "tax_wealth_structuring": "intermediate",
            "financial_data_infrastructure": "advanced",
            "hedge_fund_operations": "advanced",
        },
        "authority": "frozen data, delayed paper outcomes, independent risk/cost recalculation, audited ledgers and compliance review",
        "risk": "high_stakes_financial_research",
        "external_write_policy": "paper_only_until_separate_human_and_regulatory_authority",
    },
    {
        "adapter_id": "strategic_asset_stewardship_v1",
        "strategic_priority": 3,
        "learning_order": [
            "power_institutions_legitimacy", "information_intelligence_attention",
            "strategic_assets_capital_allocation", "technology_industry_platforms",
            "networks_talent_coordination", "resilience_geography_long_horizon",
        ],
        "title": "Governed strategic capability and asset stewardship",
        "required_subjects": {
            "power_institutions_legitimacy": "advanced",
            "information_intelligence_attention": "advanced",
            "strategic_assets_capital_allocation": "advanced",
            "technology_industry_platforms": "advanced",
            "networks_talent_coordination": "advanced",
            "resilience_geography_long_horizon": "advanced",
        },
        "authority": "public evidence, independent valuation, legal/competition review, stakeholder-harm review, owner approval and later operating outcomes",
        "risk": "high_stakes_strategy_and_capital",
        "external_write_policy": "analysis_and_proposals_only; no acquisition, capital movement, political action, deceptive influence or external communication without explicit authority",
    },
    {
        "adapter_id": "paper_market_strategy_v1",
        "strategic_priority": 2,
        "learning_order": ["markets_investing", "probability_statistics",
                           "accounting_corporate_finance", "data_statistics"],
        "title": "Delayed paper-traded market strategy",
        "safe_early_experience": True,
        "experience_entry_subjects": {
            "data_statistics": "beginner", "probability_statistics": "beginner",
            "markets_investing": "beginner", "accounting_corporate_finance": "beginner",
        },
        "required_subjects": {"data_statistics": "intermediate", "probability_statistics": "intermediate",
                              "markets_investing": "beginner", "accounting_corporate_finance": "beginner"},
        "authority": "independently published market candles observed after a frozen paper order",
        "risk": "financial",
        "external_write_policy": "paper_only_no_broker_credentials_no_capital",
    },
    {
        "adapter_id": "public_forecasting_competition_v1",
        "strategic_priority": 1,
        "learning_order": ["data_statistics", "scientific_method"],
        "title": "Public delayed forecasting challenge",
        "safe_early_experience": True,
        "experience_entry_subjects": {
            "data_statistics": "beginner", "scientific_method": "beginner",
        },
        "required_subjects": {"data_statistics": "intermediate", "scientific_method": "intermediate"},
        "authority": "official public data release after timestamped forecast commitment",
        "risk": "read_only_public_data",
        "external_write_policy": "read_only",
    },
    {
        "adapter_id": "physical_engineering_validation_v1",
        "strategic_priority": 6,
        "title": "Physical engineering build and measurement",
        "required_subjects": {"mechanical_cad": "advanced", "classical_physics": "advanced",
                              "control_robotics": "advanced"},
        "authority": "calibrated physical measurements and signed human safety receipt",
        "risk": "physical_hardware",
        "external_write_policy": "blocked_until_explicit_hardware_and_safety_approval",
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=True).encode("utf-8")).hexdigest()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _append(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(value), sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _epoch(value: str | None) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _json(url: str) -> Any:
    request = urllib.request.Request(url, headers={
        "User-Agent": "AION-real-world-experience/1.0", "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read())


def _github_issue_probe() -> dict[str, Any]:
    rows = _json("https://api.github.com/repos/python/cpython/issues?state=open&labels=type-bug&per_page=30&sort=updated")
    candidates = [row for row in rows if "pull_request" not in row]
    if not candidates:
        return {"reachable": True, "problem_available": False}
    row = candidates[0]
    snapshot = {
        "repository": "python/cpython", "issue_number": row.get("number"),
        "title": row.get("title"), "url": row.get("html_url"),
        "updated_at": row.get("updated_at"), "state": row.get("state"),
        "body_sha256": hashlib.sha256(str(row.get("body") or "").encode("utf-8")).hexdigest(),
        "labels": sorted(label.get("name") for label in row.get("labels") or [] if label.get("name")),
    }
    return {"reachable": True, "problem_available": True, "snapshot": snapshot,
            "snapshot_sha256": _digest(snapshot), "observed_at": _now()}


def _market_probe() -> dict[str, Any]:
    """Read completed public BTC/USD hourly candles; never touches a broker."""
    authority = "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60"
    payload = _json(authority)
    result = payload.get("result") or {}
    series = next((value for key, value in result.items()
                   if key != "last" and isinstance(value, list)), [])
    # Kraken's final candle may still be forming, so commit from the latest
    # completed candle and its completed predecessor.
    if len(series) < 3:
        return {"reachable": True, "market_available": False, "authority": authority}
    previous, latest = series[-3], series[-2]
    snapshot = {
        "symbol": "XBTUSD", "interval_minutes": 60,
        "candle_epoch": int(latest[0]), "previous_candle_epoch": int(previous[0]),
        "close": float(latest[4]), "previous_close": float(previous[4]),
        "authority": authority,
    }
    return {"reachable": True, "market_available": True, **snapshot,
            "snapshot_sha256": _digest(snapshot), "observed_at": _now()}


def _business_probe(repo_root: Path) -> dict[str, Any]:
    root = repo_root / ".runtime/AION_BUSINESS/business_containers/home-fixed"
    paths = [root / "business_financial_model.json", root / "business_operating_model.json",
             root / "operational_runtime_summary.json"]
    available = [path for path in paths if path.exists()]
    snapshot = [{"path": str(path.relative_to(repo_root)), "sha256": hashlib.sha256(
        path.read_bytes()).hexdigest(), "mtime": path.stat().st_mtime} for path in available]
    return {"reachable": bool(available), "workspace": "home-fixed", "sources": snapshot,
            "snapshot_sha256": _digest(snapshot) if snapshot else None, "observed_at": _now()}


def _security_scope_probe(repo_root: Path) -> dict[str, Any]:
    configured = os.getenv("AION_AUTHORIZED_SECURITY_SCOPE")
    path = Path(configured).expanduser() if configured else (
        repo_root / "backend/modules/hexcore/data/authorized_security_range/scope.json")
    scope = _read(path, {})
    targets = scope.get("targets") or []
    methods = scope.get("permitted_methods") or []
    expires = _epoch(scope.get("expires_at"))
    valid = bool(
        scope.get("owner_approved") is True
        and scope.get("isolated_range") is True
        and isinstance(targets, list) and targets
        and isinstance(methods, list) and methods
        and expires > time.time()
    )
    snapshot = {
        "scope_id": scope.get("scope_id"), "targets": sorted(map(str, targets)),
        "permitted_methods": sorted(map(str, methods)), "expires_at": scope.get("expires_at"),
        "isolated_range": scope.get("isolated_range") is True,
        "owner_approved": scope.get("owner_approved") is True,
        "destructive_testing": False, "persistence": False, "data_exfiltration": False,
    }
    return {"reachable": path.exists(), "authorized": valid,
            "status": "authorized_isolated_scope" if valid else "authorization_scope_required",
            "scope_path": str(path), "snapshot": snapshot,
            "snapshot_sha256": _digest(snapshot) if path.exists() else None}


def _security_assessment_contract(probe: Mapping[str, Any],
                                  readiness: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        "contract_id": "owned_purple_team_security_assessment_v1",
        "adapter_id": "owned_purple_team_security_assessment_v1",
        "created_at": _now(), "scope": probe["snapshot"],
        "scope_sha256": probe["snapshot_sha256"], "subject_evidence": readiness.get("subjects"),
        "success_contract": [
            "freeze the owned vulnerable baseline and target inventory",
            "demonstrate each weakness only with the minimum non-destructive proof",
            "record corresponding detection and incident-response evidence",
            "repair every validated defect and freeze regression tests",
            "independently retest the patch and at least one attack variant",
            "confirm zero out-of-scope targets, persistence, destructive actions and data exfiltration",
        ],
        "out_of_scope_targets": 0, "destructive_actions": 0, "persistence_actions": 0,
        "data_exfiltration": 0, "external_writes": 0,
        "next_stage": "isolated_range_baseline_and_authorized_assessment",
    }
    body["commitment_sha256"] = _digest(body)
    return body


def _subject_readiness(progress: Mapping[str, Any], requirements: Mapping[str, Any]) -> list[dict[str, Any]]:
    subjects = progress.get("subjects") or {}
    rows = []
    for subject_id, required in requirements.items():
        actual = str((subjects.get(subject_id) or {}).get("overall_level") or "unassessed")
        rows.append({"subject_id": subject_id, "required": required, "actual": actual,
                     "ready": LEVEL.get(actual, 0) >= LEVEL.get(str(required), 0)})
    return rows


def _readiness(progress: Mapping[str, Any], adapter: Mapping[str, Any]) -> dict[str, Any]:
    rows = _subject_readiness(progress, adapter.get("required_subjects") or {})
    entry_requirements = adapter.get("experience_entry_subjects") or {}
    entry_rows = _subject_readiness(progress, entry_requirements) if entry_requirements else rows
    qualification_ready = all(row["ready"] for row in rows)
    experience_ready = all(row["ready"] for row in entry_rows)
    return {
        "ready": qualification_ready,
        "qualification_ready": qualification_ready,
        "experience_ready": experience_ready,
        "subjects": rows,
        "experience_entry_subjects": entry_rows,
    }


def _upstream_contract(probe: Mapping[str, Any], readiness: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        "contract_id": "real_upstream_repair__python_cpython_v1",
        "adapter_id": "upstream_software_problem_and_repair_v1",
        "created_at": _now(), "problem": probe.get("snapshot"),
        "problem_snapshot_sha256": probe.get("snapshot_sha256"),
        "subject_evidence": readiness.get("subjects"),
        "execution_surface": "isolated_private_clone_pinned_before_any_patch",
        "success_contract": [
            "reproduce the reported behaviour or reject the issue as non-reproducible with evidence",
            "freeze a failing regression test before proposing a patch",
            "make the regression test and relevant upstream suite pass after the minimal patch",
            "retain full command, source revision, diff, test and counterexample receipts",
            "obtain an independent verifier result before describing the repair as successful",
        ],
        "external_pull_request": False, "external_comment": False, "external_writes": 0,
        "next_stage": "private_reproduction_and_patch_attempt",
    }
    body["commitment_sha256"] = _digest(body)
    return body


def _forecast_contract(outcomes: list[dict[str, Any]], readiness: Mapping[str, Any],
                       delay_seconds: float, *, sequence: int = 1,
                       after_anchor_cycle: int = 0) -> dict[str, Any] | None:
    eligible = [row for row in outcomes
                if int(row.get("cycle") or 0) > int(after_anchor_cycle)]
    if not eligible:
        return None
    anchor = eligible[-1]
    weather = (anchor.get("outcomes") or {}).get("madrid_weather") or {}
    if not weather.get("reachable") or weather.get("temperature") is None or weather.get("wind") is None:
        return None
    created_epoch = time.time()
    temperature = float(weather["temperature"])
    wind = float(weather["wind"])
    body = {
        "contract_id": f"real_public_forecast__madrid_weather_v1__{sequence:04d}",
        "sequence": sequence,
        "adapter_id": "public_forecasting_competition_v1",
        "created_at": _now(), "created_epoch": created_epoch,
        "not_before_epoch": created_epoch + max(300.0, float(delay_seconds)),
        "anchor_cycle": int(anchor.get("cycle") or 0),
        "anchor_outcome_sha256": anchor.get("outcome_sha256"),
        "subject_evidence": readiness.get("subjects"),
        "forecast": {
            "temperature_min": temperature - 5.0, "temperature_max": temperature + 5.0,
            "wind_max": max(15.0, wind + 10.0),
        },
        "selection_rule": "first reachable Madrid public sensor row after not_before_epoch",
        "scoring_rule": "temperature inside frozen interval and wind no greater than frozen ceiling",
        "external_writes": 0, "owner_interventions": 0,
    }
    body["commitment_sha256"] = _digest(body)
    return body


def _close_forecast(contract: Mapping[str, Any], outcomes: list[dict[str, Any]]) -> dict[str, Any] | None:
    selected = None
    for row in outcomes:
        weather = (row.get("outcomes") or {}).get("madrid_weather") or {}
        if int(row.get("cycle") or 0) <= int(contract.get("anchor_cycle") or 0):
            continue
        if _epoch(row.get("observed_at")) < float(contract.get("not_before_epoch") or 0):
            continue
        if weather.get("reachable") and weather.get("temperature") is not None and weather.get("wind") is not None:
            selected = row
            break
    if selected is None:
        return None
    weather = selected["outcomes"]["madrid_weather"]
    forecast = contract["forecast"]
    passed = (float(forecast["temperature_min"]) <= float(weather["temperature"])
              <= float(forecast["temperature_max"])
              and float(weather["wind"]) <= float(forecast["wind_max"]))
    capsule = {
        "capsule_id": (
            f"real_forecast_outcome__madrid_weather_v1__"
            f"{int(contract.get('sequence') or 1):04d}"
        ),
        "adapter_id": contract["adapter_id"], "created_at": _now(),
        "commitment_sha256": contract["commitment_sha256"],
        "anchor_outcome_sha256": contract["anchor_outcome_sha256"],
        "later_outcome_sha256": selected.get("outcome_sha256"),
        "later_cycle": selected.get("cycle"), "later_observed_at": selected.get("observed_at"),
        "elapsed_seconds": max(0.0, _epoch(selected.get("observed_at"))
                               - float(contract.get("created_epoch") or 0)),
        "forecast": forecast,
        "observed": {"temperature": weather["temperature"], "wind": weather["wind"],
                     "authority": weather.get("authority")},
        "outcome_success": passed, "verified_real_outcome": True,
        "world_model_update_required": not passed,
        "external_writes": 0, "unsafe_actions": 0,
        "claim_boundary": "One delayed independently observed forecast outcome; not broad forecasting mastery.",
    }
    capsule["capsule_sha256"] = _digest(capsule)
    return capsule


def _paper_market_contract(probe: Mapping[str, Any], readiness: Mapping[str, Any],
                           delay_seconds: float, *, sequence: int = 1,
                           after_anchor_candle_epoch: int = 0) -> dict[str, Any] | None:
    if not probe.get("reachable") or not probe.get("market_available"):
        return None
    if int(probe.get("candle_epoch") or 0) <= int(after_anchor_candle_epoch):
        return None
    entry = float(probe["close"])
    previous = float(probe["previous_close"])
    direction = "long" if entry >= previous else "short"
    created_epoch = time.time()
    body = {
        "contract_id": f"real_paper_market__xbtusd_hourly_momentum_v1__{sequence:04d}",
        "sequence": sequence,
        "adapter_id": "paper_market_strategy_v1",
        "created_at": _now(), "created_epoch": created_epoch,
        "not_before_epoch": created_epoch + max(300.0, float(delay_seconds)),
        "symbol": probe["symbol"], "interval_minutes": probe["interval_minutes"],
        "anchor_candle_epoch": int(probe["candle_epoch"]),
        "anchor_snapshot_sha256": probe["snapshot_sha256"],
        "entry_price": entry, "direction": direction,
        "hypothetical_notional": 10_000.0, "round_trip_cost_bps": 10.0,
        "subject_evidence": readiness.get("subjects"),
        "selection_rule": "first independently published completed XBTUSD hourly candle after both the frozen candle and not_before_epoch",
        "scoring_rule": "directional close-to-close return minus frozen round-trip costs; positive net return is success",
        "broker_credentials": False, "orders_submitted": 0, "capital_at_risk": 0,
        "external_writes": 0, "owner_interventions": 0,
    }
    body["commitment_sha256"] = _digest(body)
    return body


def _close_paper_market(contract: Mapping[str, Any], probe: Mapping[str, Any]) -> dict[str, Any] | None:
    if (not probe.get("reachable") or not probe.get("market_available")
            or int(probe.get("candle_epoch") or 0) <= int(contract.get("anchor_candle_epoch") or 0)):
        return None
    entry = float(contract["entry_price"])
    exit_price = float(probe["close"])
    sign = 1.0 if contract["direction"] == "long" else -1.0
    gross_return = sign * ((exit_price - entry) / entry)
    net_return = gross_return - float(contract["round_trip_cost_bps"]) / 10_000.0
    pnl = float(contract["hypothetical_notional"]) * net_return
    capsule = {
        "capsule_id": (
            f"real_paper_market_outcome__xbtusd_hourly_momentum_v1__"
            f"{int(contract.get('sequence') or 1):04d}"
        ),
        "adapter_id": contract["adapter_id"], "created_at": _now(),
        "commitment_sha256": contract["commitment_sha256"],
        "anchor_snapshot_sha256": contract["anchor_snapshot_sha256"],
        "later_snapshot_sha256": probe["snapshot_sha256"],
        "anchor_candle_epoch": contract["anchor_candle_epoch"],
        "later_candle_epoch": probe["candle_epoch"],
        "direction": contract["direction"], "entry_price": entry, "exit_price": exit_price,
        "gross_return": gross_return, "net_return_after_costs": net_return,
        "hypothetical_pnl": pnl, "outcome_success": net_return > 0,
        "verified_real_outcome": True, "world_model_update_required": net_return <= 0,
        "broker_credentials": False, "orders_submitted": 0, "capital_at_risk": 0,
        "external_writes": 0, "unsafe_actions": 0,
        "authority": probe.get("authority"),
        "claim_boundary": "One delayed paper-market outcome after frozen costs; not evidence of persistent alpha or investment competence.",
    }
    capsule["capsule_sha256"] = _digest(capsule)
    return capsule


def run_cycle(*, repo_root: Path, progress_path: Path | None = None,
              state_path: Path | None = None, result_path: Path | None = None,
              github_probe: Callable[[], dict[str, Any]] = _github_issue_probe,
              market_probe: Callable[[], dict[str, Any]] = _market_probe,
              public_outcome_ledger: Path | None = None,
              forecast_delay_seconds: float | None = None,
              market_delay_seconds: float | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    base = root / "backend/modules/hexcore/data/real_world_experience_adapters"
    progress_path = progress_path or root / "results/aion_progressive_competency_status.json"
    state_path = state_path or base / "state.json"
    result_path = result_path or root / "results/hexcore_real_world_experience_adapters.json"
    public_outcome_ledger = public_outcome_ledger or root / "results/hexcore_prospective_cross_domain_outcomes.jsonl"
    if forecast_delay_seconds is None:
        forecast_delay_seconds = float(os.getenv("AION_ADVANCED_FORECAST_DELAY", "900"))
    if market_delay_seconds is None:
        market_delay_seconds = float(os.getenv("AION_PAPER_MARKET_DELAY", "3600"))
    progress = _read(progress_path, {})
    public_outcomes = _jsonl(public_outcome_ledger)
    with exclusive_file_lock(base / "adapters.lock"):
        state = _read(state_path, {"schema_version": SCHEMA, "created_at": _now(), "contracts": {}})
        state.setdefault("completed_contracts", {})
        state.setdefault("completed_history", {})
        state.setdefault("outcome_sequences", {})
        state.setdefault("verified_outcomes", [])
        latest_verified_outcome: dict[str, Any] = {}
        rows = []
        for adapter in ADAPTERS:
            readiness = _readiness(progress, adapter)
            authority_probe: dict[str, Any] = {"reachable": False, "status": "not_probed_until_ready"}
            status = "learning_required"
            operational_ready = bool(
                readiness["ready"]
                or (adapter.get("safe_early_experience") and readiness["experience_ready"])
            )
            if operational_ready:
                if adapter["adapter_id"] == "owned_purple_team_security_assessment_v1":
                    authority_probe = _security_scope_probe(root)
                    if authority_probe.get("authorized"):
                        status = "authorized_scope_locked_for_lab_assessment"
                        if adapter["adapter_id"] not in state["contracts"]:
                            contract = _security_assessment_contract(authority_probe, readiness)
                            state["contracts"][adapter["adapter_id"]] = contract
                            _append(base / "commitment_ledger.jsonl", contract)
                    else:
                        status = "authorization_scope_required"
                elif adapter["adapter_id"] == "upstream_software_problem_and_repair_v1":
                    existing = (state.get("contracts") or {}).get(adapter["adapter_id"])
                    existing_labels = set(((existing or {}).get("problem") or {}).get("labels") or [])
                    if existing and "type-bug" not in existing_labels:
                        retirement = {
                            "contract_id": existing.get("contract_id"),
                            "commitment_sha256": existing.get("commitment_sha256"),
                            "retired_at": _now(),
                            "reason": "intake_not_labeled_type_bug_and_therefore_not_a_repair_mission",
                            "executed": False, "external_writes": 0,
                        }
                        state.setdefault("retired_contracts", []).append(retirement)
                        _append(base / "retired_contract_ledger.jsonl", retirement)
                        state["contracts"].pop(adapter["adapter_id"], None)
                        existing = None
                    if existing:
                        authority_probe = {"reachable": True, "problem_available": True,
                                           "snapshot": existing.get("problem"),
                                           "snapshot_sha256": existing.get("problem_snapshot_sha256"),
                                           "status": "frozen_contract_reused_without_requery"}
                    else:
                        try:
                            authority_probe = github_probe()
                        except Exception as error:
                            authority_probe = {"reachable": False, "error": type(error).__name__}
                    status = "real_problem_available" if authority_probe.get("problem_available") else "authority_unavailable"
                    if status == "real_problem_available" and adapter["adapter_id"] not in state["contracts"]:
                        contract = _upstream_contract(authority_probe, readiness)
                        state["contracts"][adapter["adapter_id"]] = contract
                        _append(base / "commitment_ledger.jsonl", contract)
                elif adapter["adapter_id"] == "tessaris_business_outcome_v1":
                    authority_probe = _business_probe(root)
                    status = "ready_for_owner_approved_metric_contract" if authority_probe["reachable"] else "authority_unavailable"
                elif adapter["adapter_id"] == "public_forecasting_competition_v1":
                    status = "ready_for_read_only_precommitment"
                    authority_probe = {"reachable": bool(public_outcomes),
                                       "status": "independent_public_outcome_ledger"}
                    completed = state["completed_contracts"].get(adapter["adapter_id"])
                    forecast_contract = state["contracts"].get(adapter["adapter_id"])
                    completed_capsule = (_read(
                        base / "capsules" / f"{completed['capsule_id']}.json", {}
                    ) if completed else {})
                    last_anchor_cycle = int(completed_capsule.get("later_cycle") or 0)
                    if forecast_contract is None:
                        sequence = int(state["outcome_sequences"].get(adapter["adapter_id"]) or 0) + 1
                        forecast_contract = _forecast_contract(
                            public_outcomes, readiness, float(forecast_delay_seconds),
                            sequence=sequence, after_anchor_cycle=last_anchor_cycle)
                        if forecast_contract is not None:
                            state["outcome_sequences"][adapter["adapter_id"]] = sequence
                            state["contracts"][adapter["adapter_id"]] = forecast_contract
                            _append(base / "commitment_ledger.jsonl", forecast_contract)
                    if forecast_contract is not None:
                        status = "waiting_for_later_public_forecast_outcome"
                        if time.time() >= float(forecast_contract["not_before_epoch"]):
                            latest_verified_outcome = _close_forecast(forecast_contract, public_outcomes) or {}
                            if latest_verified_outcome:
                                capsule_path = base / "capsules" / f"{latest_verified_outcome['capsule_id']}.json"
                                _write(capsule_path, latest_verified_outcome)
                                if latest_verified_outcome["capsule_id"] not in state["verified_outcomes"]:
                                    state["verified_outcomes"].append(latest_verified_outcome["capsule_id"])
                                completion = {
                                    "capsule_id": latest_verified_outcome["capsule_id"],
                                    "capsule_sha256": latest_verified_outcome["capsule_sha256"],
                                    "completed_at": _now(),
                                }
                                state["completed_contracts"][adapter["adapter_id"]] = completion
                                state["completed_history"].setdefault(adapter["adapter_id"], []).append(completion)
                                state["contracts"].pop(adapter["adapter_id"], None)
                                _append(base / "outcome_ledger.jsonl", latest_verified_outcome)
                                status = "real_forecast_outcome_recorded"
                    elif completed:
                        status = "real_forecast_outcome_recorded_waiting_for_new_anchor"
                        latest_verified_outcome = completed_capsule
                elif adapter["adapter_id"] == "paper_market_strategy_v1":
                    completed = state["completed_contracts"].get(adapter["adapter_id"])
                    market_contract = state["contracts"].get(adapter["adapter_id"])
                    completed_capsule = (_read(
                        base / "capsules" / f"{completed['capsule_id']}.json", {}
                    ) if completed else {})
                    try:
                        authority_probe = market_probe()
                    except Exception as error:
                        authority_probe = {"reachable": False, "error": type(error).__name__}
                    last_anchor_candle = int(completed_capsule.get("later_candle_epoch") or 0)
                    if market_contract is None:
                        sequence = int(state["outcome_sequences"].get(adapter["adapter_id"]) or 0) + 1
                        market_contract = _paper_market_contract(
                            authority_probe, readiness, float(market_delay_seconds),
                            sequence=sequence, after_anchor_candle_epoch=last_anchor_candle)
                        if market_contract is not None:
                            state["outcome_sequences"][adapter["adapter_id"]] = sequence
                            state["contracts"][adapter["adapter_id"]] = market_contract
                            _append(base / "commitment_ledger.jsonl", market_contract)
                    status = ("waiting_for_later_paper_market_outcome" if market_contract
                              else ("real_paper_market_outcome_recorded_waiting_for_new_candle"
                                    if completed else "authority_unavailable"))
                    if (market_contract is not None
                            and time.time() >= float(market_contract["not_before_epoch"])):
                        latest_verified_outcome = _close_paper_market(
                            market_contract, authority_probe) or {}
                        if latest_verified_outcome:
                            capsule_path = base / "capsules" / f"{latest_verified_outcome['capsule_id']}.json"
                            _write(capsule_path, latest_verified_outcome)
                            if latest_verified_outcome["capsule_id"] not in state["verified_outcomes"]:
                                state["verified_outcomes"].append(latest_verified_outcome["capsule_id"])
                            completion = {
                                "capsule_id": latest_verified_outcome["capsule_id"],
                                "capsule_sha256": latest_verified_outcome["capsule_sha256"],
                                "completed_at": _now(),
                            }
                            state["completed_contracts"][adapter["adapter_id"]] = completion
                            state["completed_history"].setdefault(adapter["adapter_id"], []).append(completion)
                            state["contracts"].pop(adapter["adapter_id"], None)
                            _append(base / "outcome_ledger.jsonl", latest_verified_outcome)
                            status = "real_paper_market_outcome_recorded"
                    elif completed and not latest_verified_outcome:
                        latest_verified_outcome = completed_capsule
                elif adapter["adapter_id"] == "prediction_market_intelligence_v1":
                    status = (
                        "ready_for_live_public_prediction_market_research_and_delayed_paper_scoring"
                        if readiness["ready"] else
                        "active_read_only_experience_while_learning"
                    )
                    authority_probe = {
                        "reachable": True,
                        "status": "public_market_data_only",
                        "credentials_loaded": False,
                        "live_orders": 0,
                        "live_capital_at_risk": 0,
                    }
                elif adapter["adapter_id"] == "institutional_finance_intelligence_v1":
                    status = "ready_for_governed_quantitative_fund_capstone"
                    authority_probe = {"reachable": True,
                                       "status": "requires_frozen_data_and_delayed_paper_outcomes"}
                elif adapter["adapter_id"] == "strategic_asset_stewardship_v1":
                    status = "ready_for_owner_scoped_strategic_asset_mission"
                    authority_probe = {
                        "reachable": True,
                        "status": "awaiting_owner_defined_industry_capital_envelope_and_jurisdiction",
                        "permitted_output": "ranked_build_buy_partner_divest_proposal",
                        "capital_movement": 0,
                        "external_actions": 0,
                    }
                else:
                    status = "hardware_and_safety_approval_required"
                    authority_probe = {"reachable": False, "status": "no_signed_hardware_authority"}
            contract = (state.get("contracts") or {}).get(adapter["adapter_id"])
            if contract and status == "real_problem_available":
                status = "real_problem_locked_for_private_repair"
            rows.append({**adapter, "readiness": readiness, "status": status,
                         "authority_probe": authority_probe, "active_contract": contract or {}})
        state.update({"schema_version": SCHEMA, "adapters": rows, "updated_at": _now(),
                      "cycles": int(state.get("cycles") or 0) + 1})
        _write(state_path, state)
        gated = [row for row in rows if not row["readiness"]["ready"]]
        next_learning_gate: dict[str, Any] = {}
        if gated:
            closest = min(gated, key=lambda row: (int(row.get("strategic_priority") or 99), sum(
                max(0, LEVEL.get(str(req["required"]), 0) - LEVEL.get(str(req["actual"]), 0))
                for req in row["readiness"]["subjects"])))
            missing = [row for row in closest["readiness"]["subjects"] if not row["ready"]]
            if missing:
                learning_order = list(closest.get("learning_order") or [])
                order = {subject_id: index for index, subject_id in enumerate(learning_order)}
                next_subject = min(missing, key=lambda row: (
                    order.get(str(row["subject_id"]), len(order)),
                    max(0, LEVEL.get(str(row["required"]), 0) - LEVEL.get(str(row["actual"]), 0)),
                    str(row["subject_id"])))
                next_learning_gate = {"adapter_id": closest["adapter_id"],
                                      "subject_id": next_subject["subject_id"],
                                      "actual": next_subject["actual"],
                                      "required": next_subject["required"]}
        result = {
            "schema_version": SCHEMA, "status": "active", "passed": True,
            "adapter_count": len(rows), "ready": sum(row["readiness"]["ready"] for row in rows),
            "experience_ready": sum(
                bool(row["readiness"]["ready"]
                     or (row.get("safe_early_experience")
                         and row["readiness"]["experience_ready"]))
                for row in rows
            ),
            "qualification_ready": sum(row["readiness"]["qualification_ready"] for row in rows),
            "active_real_contracts": sum(bool(row["active_contract"]) for row in rows),
            "learning_gated": sum(not row["readiness"]["ready"] for row in rows),
            "external_writes": 0, "live_capital_at_risk": 0, "physical_actions": 0,
            "adapters": rows, "updated_at": time.time(),
            "next_learning_gate": next_learning_gate,
            "verified_real_outcomes": len(state.get("verified_outcomes") or []),
            "latest_verified_outcome": latest_verified_outcome,
            "claim_boundary": (
                "Adapters and frozen contracts are execution infrastructure. Only later independently "
                "verified receipts count as real experience; readiness or intake is not mission success."
            ),
        }
        _write(result_path, result)
        return result


if __name__ == "__main__":
    print(json.dumps(run_cycle(repo_root=Path(os.getenv("AION_REPO_ROOT", "."))), indent=2))
