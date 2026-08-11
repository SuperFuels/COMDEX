from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.open_objective_family_invention import run


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload), encoding="utf-8")


def test_new_family_requires_executor_authority_and_source_disjoint_transfer(tmp_path: Path) -> None:
    goal_id = "tier-five-project"
    _write(tmp_path / "data/goals/goals.json", {"completed": [], "goals": [{
        "name": goal_id, "created_at": "2026-08-02T10:00:00+00:00"}]})
    contract = {"objective_id": goal_id, "lane": "useful_work", "family": "software_tool",
                "difficulty_tier": 5, "required_independent_receipts": 4,
                "cross_domain_partner": "cloud_devops_sre",
                "open_family_requirement": "invent_new_objective_family_executor_and_outcome_authority"}
    _write(tmp_path / "backend/modules/hexcore/data/autonomous_capability_research_executive/state.json",
           {"generations": [{"commitment": {"portfolio": [contract]}}]})
    projects = [
        {"project_id": "development", "status": "consequence_confirmed", "artifact_sha256": "dev",
         "evaluation": {"authorities_checked": ["cpython", "node", "numpy_release", "madrid_weather"],
                        "world_changes": [], "internal_self_repair_triggered": False}},
        {"project_id": "transfer", "status": "consequence_confirmed", "artifact_sha256": "transfer",
         "evaluation": {"authorities_checked": ["cpython", "node", "numpy_release", "madrid_weather"],
                        "world_changes": ["madrid_weather"], "internal_self_repair_triggered": False}},
    ]
    _write(tmp_path / "backend/modules/hexcore/data/situated_cross_domain_projects/state.json",
           {"projects": projects})
    kwargs = dict(repo_root=tmp_path, state_path=tmp_path / "family-state.json",
                  workspace_root=tmp_path / "artifacts", result_path=tmp_path / "result.json")
    first = run(**kwargs)
    assert first["passed"] is False and first["gate"]["precommitments"] == 1
    second = run(**kwargs)
    assert second["passed"] is True
    assert second["invented_family"] == "situated_operational_resilience"
    assert second["gate"]["independent_authority_receipts"] == 1
    assert second["gate"]["source_disjoint_transfers"] == 1
    receipt = second["new_receipts"][0]
    assert receipt["authority_receipt_sha256"] != receipt["receipt_sha256"]
    artifact = json.loads((tmp_path / receipt["artifact"]).read_text())
    assert artifact["development_authorities"] == ["cpython", "node", "numpy_release"]
    assert artifact["transfer_authorities"] == ["madrid_weather"]
    assert sum(row["accepted"] for row in artifact["tournament"]) == 1
