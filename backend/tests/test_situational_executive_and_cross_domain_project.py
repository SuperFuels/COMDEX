from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.situational_executive_driver import run as run_situation
from backend.modules.hexcore.situated_cross_domain_project_engine import run as run_project


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload), encoding="utf-8")


def _row(cycle: int, observed_at: str, suffix: str) -> dict:
    return {"cycle": cycle, "observed_at": observed_at, "outcome_sha256": "outcome-" + suffix,
            "acquisition_failures": [], "internal_self_repair_triggered": False,
            "outcomes": {
                "cpython": {"reachable": True, "revision": "python-" + suffix},
                "node": {"reachable": True, "revision": "node-stable"},
                "numpy_release": {"reachable": True, "revision": "numpy-stable"},
                "madrid_weather": {"reachable": True, "revision": "weather-" + suffix},
            }}


def test_situation_drives_cross_domain_project_and_later_evidence(tmp_path: Path) -> None:
    subjects = {name: {"subject_id": name, "name": name, "overall_level": "advanced"}
                for name in ("software_engineering", "python", "testing_debugging",
                             "algorithms_data_structures", "scientific_method", "mathematics", "english")}
    _write(tmp_path / "results/aion_progressive_competency_status.json", {"subjects": subjects})
    _write(tmp_path / "results/hexcore_autonomous_capability_research_executive.json",
           {"portfolio": [{"difficulty_tier": 4}]})
    _write(tmp_path / "results/hexcore_autonomous_goal_consequence_arbiter.json",
           {"gate": {"consequence_confirmed": 9}})
    _write(tmp_path / "results/hexcore_open_cross_domain_authority_factory.json",
           {"gate": {"eligible_goals": 0}})
    _write(tmp_path / "results/hexcore_prospective_cross_domain_outcome.json",
           {"gate": {"independent_authority_families": 3}})
    _write(tmp_path / "data/goals/goals.json", {"completed": [], "goals": [{
        "name": "north-star-work", "objective": "Increase verified intelligence through useful work.",
        "priority": 10, "origin": "owner_authorized",
    }]})
    situation = run_situation(repo_root=tmp_path, state_path=tmp_path / "situation-state.json",
                              result_path=tmp_path / "results/hexcore_situational_executive_driver.json")
    assert situation["passed"] is True
    assert situation["situation"]["current_driver"]["need_id"] == "missing_tier4_diagnostic_authority"
    assert situation["gate"]["advanced_or_expert_resources"] == 7
    assert situation["situation"]["authority_boundary"]

    ledger = tmp_path / "outcomes.jsonl"
    ledger.write_text(json.dumps(_row(1, "2026-08-02T10:00:00+00:00", "a")) + "\n", encoding="utf-8")
    kwargs = dict(repo_root=tmp_path, state_path=tmp_path / "project-state.json",
                  outcome_ledger=ledger, workspace_root=tmp_path / "project-artifacts",
                  result_path=tmp_path / "project-result.json", minimum_delay_seconds=60)
    first = run_project(**kwargs)
    assert first["passed"] is False and first["active_project"]
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_row(2, "2026-08-02T10:02:00+00:00", "b")) + "\n")
    second = run_project(**kwargs)
    assert second["passed"] is True
    assert second["gate"]["fresh_domain_evidence_receipts"] == 7
    assert second["newly_closed"]["evaluation"]["failure_attribution"] == "external_world_change"
    assert second["gate"]["world_changes_misrouted_to_self_repair"] == 0
