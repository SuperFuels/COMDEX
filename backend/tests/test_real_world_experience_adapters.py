import json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.hexcore import real_world_experience_adapters as adapters
from backend.modules.hexcore.real_world_experience_adapters import run_cycle


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_only_learned_real_world_adapter_activates(tmp_path: Path) -> None:
    progress = {"subjects": {
        "software_engineering": {"overall_level": "advanced"},
        "testing_debugging": {"overall_level": "advanced"},
    }}
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, progress)
    probe = lambda: {"reachable": True, "problem_available": True, "snapshot": {
        "repository": "python/cpython", "issue_number": 42, "title": "real issue",
        "url": "https://github.com/python/cpython/issues/42", "body_sha256": "abc",
        "labels": ["type-bug"],
    }, "snapshot_sha256": "snapshot"}
    result = run_cycle(repo_root=tmp_path, progress_path=progress_path, github_probe=probe)
    assert result["ready"] == 1
    assert result["active_real_contracts"] == 1
    assert result["learning_gated"] == 8
    assert result["external_writes"] == 0
    upstream = next(row for row in result["adapters"]
                    if row["adapter_id"] == "upstream_software_problem_and_repair_v1")
    assert upstream["status"] == "real_problem_locked_for_private_repair"
    assert upstream["active_contract"]["external_pull_request"] is False
    assert upstream["active_contract"]["commitment_sha256"]


def test_safe_read_only_experience_starts_before_full_qualification(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, {"subjects": {
        "probabilistic_forecasting_calibration": {"overall_level": "beginner"},
    }})
    result = run_cycle(
        repo_root=tmp_path, progress_path=progress_path,
        github_probe=lambda: {"reachable": False},
    )
    prediction = next(row for row in result["adapters"]
                      if row["adapter_id"] == "prediction_market_intelligence_v1")
    assert prediction["readiness"]["qualification_ready"] is False
    assert prediction["readiness"]["experience_ready"] is True
    assert prediction["status"] == "active_read_only_experience_while_learning"
    assert prediction["authority_probe"]["live_orders"] == 0
    assert result["experience_ready"] == 1
    assert result["qualification_ready"] == 0


def test_adapter_contract_is_idempotent_and_does_not_modify_progress(tmp_path: Path) -> None:
    progress = {"subjects": {
        "software_engineering": {"overall_level": "expert"},
        "testing_debugging": {"overall_level": "advanced"},
    }}
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, progress)
    counter = {"calls": 0}

    def probe() -> dict:
        counter["calls"] += 1
        return {"reachable": True, "problem_available": True,
                "snapshot": {"issue_number": counter["calls"], "labels": ["type-bug"]},
                "snapshot_sha256": str(counter["calls"])}

    first = run_cycle(repo_root=tmp_path, progress_path=progress_path, github_probe=probe)
    second = run_cycle(repo_root=tmp_path, progress_path=progress_path, github_probe=probe)
    first_contract = next(row for row in first["adapters"]
                          if row["adapter_id"] == "upstream_software_problem_and_repair_v1")["active_contract"]
    second_contract = next(row for row in second["adapters"]
                           if row["adapter_id"] == "upstream_software_problem_and_repair_v1")["active_contract"]
    assert first_contract == second_contract
    assert json.loads(progress_path.read_text(encoding="utf-8")) == progress
    assert len((tmp_path / "backend/modules/hexcore/data/real_world_experience_adapters/commitment_ledger.jsonl").read_text().splitlines()) == 1


def test_physical_adapter_cannot_activate_without_subjects_and_approval(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, {"subjects": {}})
    result = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                       github_probe=lambda: {"reachable": False})
    physical = next(row for row in result["adapters"]
                    if row["adapter_id"] == "physical_engineering_validation_v1")
    assert physical["status"] == "learning_required"
    assert result["physical_actions"] == 0
    assert result["live_capital_at_risk"] == 0


def test_delayed_public_forecast_uses_later_independent_receipt(tmp_path: Path, monkeypatch) -> None:
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, {"subjects": {
        "data_statistics": {"overall_level": "intermediate"},
        "scientific_method": {"overall_level": "intermediate"},
    }})
    ledger = tmp_path / "results/public.jsonl"
    base = 2_000_000_000.0
    anchor = {
        "cycle": 10, "observed_at": datetime.fromtimestamp(base, timezone.utc).isoformat(),
        "outcome_sha256": "anchor-sha",
        "outcomes": {"madrid_weather": {"reachable": True, "temperature": 20.0,
                                            "wind": 7.0, "authority": "public-sensor"}},
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(anchor) + "\n", encoding="utf-8")
    monkeypatch.setattr(adapters.time, "time", lambda: base)
    first = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                      public_outcome_ledger=ledger, forecast_delay_seconds=300,
                      github_probe=lambda: {"reachable": False})
    forecast = next(row for row in first["adapters"]
                    if row["adapter_id"] == "public_forecasting_competition_v1")
    assert forecast["status"] == "waiting_for_later_public_forecast_outcome"
    later = {
        "cycle": 11, "observed_at": datetime.fromtimestamp(base + 301, timezone.utc).isoformat(),
        "outcome_sha256": "later-sha",
        "outcomes": {"madrid_weather": {"reachable": True, "temperature": 22.0,
                                            "wind": 8.0, "authority": "public-sensor"}},
    }
    ledger.write_text(json.dumps(anchor) + "\n" + json.dumps(later) + "\n", encoding="utf-8")
    monkeypatch.setattr(adapters.time, "time", lambda: base + 301)
    second = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                       public_outcome_ledger=ledger, forecast_delay_seconds=300,
                       github_probe=lambda: {"reachable": False})
    forecast = next(row for row in second["adapters"]
                    if row["adapter_id"] == "public_forecasting_competition_v1")
    assert forecast["status"] == "real_forecast_outcome_recorded"
    assert second["verified_real_outcomes"] == 1
    assert second["latest_verified_outcome"]["later_outcome_sha256"] == "later-sha"
    assert second["latest_verified_outcome"]["outcome_success"] is True

    newer = {
        "cycle": 12, "observed_at": datetime.fromtimestamp(base + 602, timezone.utc).isoformat(),
        "outcome_sha256": "new-anchor-sha",
        "outcomes": {"madrid_weather": {"reachable": True, "temperature": 21.0,
                                            "wind": 7.5, "authority": "public-sensor"}},
    }
    ledger.write_text(
        json.dumps(anchor) + "\n" + json.dumps(later) + "\n" + json.dumps(newer) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(adapters.time, "time", lambda: base + 602)
    third = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                      public_outcome_ledger=ledger, forecast_delay_seconds=300,
                      github_probe=lambda: {"reachable": False})
    forecast = next(row for row in third["adapters"]
                    if row["adapter_id"] == "public_forecasting_competition_v1")
    assert forecast["status"] == "waiting_for_later_public_forecast_outcome"
    assert forecast["active_contract"]["anchor_cycle"] == 12
    assert forecast["active_contract"]["contract_id"].endswith("__0002")
    assert third["verified_real_outcomes"] == 1


def test_paper_market_contract_is_frozen_then_scored_on_a_later_candle(
        tmp_path: Path, monkeypatch) -> None:
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, {"subjects": {
        "data_statistics": {"overall_level": "intermediate"},
        "probability_statistics": {"overall_level": "intermediate"},
        "markets_investing": {"overall_level": "advanced"},
        "accounting_corporate_finance": {"overall_level": "beginner"},
    }})
    base = 2_100_000_000.0
    observations = iter((
        {"reachable": True, "market_available": True, "symbol": "XBTUSD",
         "interval_minutes": 60, "candle_epoch": 1000, "previous_close": 99.0,
         "close": 100.0, "snapshot_sha256": "market-anchor", "authority": "public-market"},
        {"reachable": True, "market_available": True, "symbol": "XBTUSD",
         "interval_minutes": 60, "candle_epoch": 1060, "previous_close": 100.0,
         "close": 102.0, "snapshot_sha256": "market-later", "authority": "public-market"},
    ))
    monkeypatch.setattr(adapters.time, "time", lambda: base)
    first = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                      market_probe=lambda: next(observations), market_delay_seconds=300,
                      github_probe=lambda: {"reachable": False})
    paper = next(row for row in first["adapters"]
                 if row["adapter_id"] == "paper_market_strategy_v1")
    assert paper["status"] == "waiting_for_later_paper_market_outcome"
    assert paper["active_contract"]["capital_at_risk"] == 0
    assert paper["active_contract"]["direction"] == "long"

    monkeypatch.setattr(adapters.time, "time", lambda: base + 301)
    second = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                       market_probe=lambda: next(observations), market_delay_seconds=300,
                       github_probe=lambda: {"reachable": False})
    paper = next(row for row in second["adapters"]
                 if row["adapter_id"] == "paper_market_strategy_v1")
    assert paper["status"] == "real_paper_market_outcome_recorded"
    assert second["latest_verified_outcome"]["later_snapshot_sha256"] == "market-later"
    assert second["latest_verified_outcome"]["net_return_after_costs"] > 0
    assert second["live_capital_at_risk"] == 0


def test_business_adapter_uses_current_finance_curriculum_subject(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, {"subjects": {
        "business_management": {"overall_level": "beginner"},
        "accounting_corporate_finance": {"overall_level": "beginner"},
    }})
    result = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                       github_probe=lambda: {"reachable": False})
    business = next(row for row in result["adapters"]
                    if row["adapter_id"] == "tessaris_business_outcome_v1")
    assert business["readiness"]["ready"] is True
    assert {row["subject_id"] for row in business["readiness"]["subjects"]} == {
        "business_management", "accounting_corporate_finance",
    }


def test_security_assessment_fails_closed_without_scope_and_locks_owned_range(
        tmp_path: Path) -> None:
    subject_ids = [
        "cybersecurity", "application_web_api_security", "network_wireless_security",
        "cloud_identity_container_security", "adversary_emulation_penetration_testing",
        "exploit_analysis_reverse_engineering",
        "detection_threat_hunting_incident_response", "cryptography_protocol_security",
        "hardware_embedded_ot_security", "security_research_disclosure",
        "security_architecture_operations",
    ]
    progress_path = tmp_path / "results/progress.json"
    _write(progress_path, {"subjects": {
        subject_id: {"overall_level": "advanced"} for subject_id in subject_ids
    }})
    first = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                      github_probe=lambda: {"reachable": False})
    security = next(row for row in first["adapters"]
                    if row["adapter_id"] == "owned_purple_team_security_assessment_v1")
    assert security["status"] == "authorization_scope_required"
    assert security["active_contract"] == {}

    scope_path = tmp_path / "backend/modules/hexcore/data/authorized_security_range/scope.json"
    _write(scope_path, {
        "scope_id": "owned-range-1", "owner_approved": True, "isolated_range": True,
        "targets": ["lab.local"], "permitted_methods": ["non_destructive_validation"],
        "expires_at": "2099-01-01T00:00:00+00:00",
    })
    second = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                       github_probe=lambda: {"reachable": False})
    security = next(row for row in second["adapters"]
                    if row["adapter_id"] == "owned_purple_team_security_assessment_v1")
    assert security["status"] == "authorized_scope_locked_for_lab_assessment"
    assert security["active_contract"]["scope"]["targets"] == ["lab.local"]
    assert security["active_contract"]["destructive_actions"] == 0
    assert security["active_contract"]["data_exfiltration"] == 0
