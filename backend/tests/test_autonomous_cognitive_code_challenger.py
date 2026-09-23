from __future__ import annotations

import json
import shutil
from pathlib import Path

from backend.modules.hexcore.autonomous_cognitive_code_challenger import run_once
from backend.modules.hexcore.executive_skills_library import ExecutiveSkillsLibrary


FAMILIES = ["research_investigation", "document_evidence", "software_tool",
            "data_decision", "mathematical_reasoning"]


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _objective(family: str, method: str, *, policy_id: str | None = None,
               confirmed: bool = False) -> dict:
    selection = {"method": method, "reason": "selected_from_objective_and_operating_context"}
    if policy_id:
        selection.update({"policy_id": policy_id, "reason": "verified_cognitive_route_champion"})
    row = {"family": family, "work_system": {"method_selection": selection}}
    if confirmed:
        row.update({"status": "consequence_confirmed", "evaluation": {"passed": True}})
    return row


def test_private_code_challenger_requires_later_operational_confirmation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    champion = repo / "backend/modules/hexcore/executive_skills_library.py"
    champion.parent.mkdir(parents=True)
    source_root = Path(__file__).resolve().parents[2]
    shutil.copy(source_root / "backend/modules/hexcore/executive_skills_library.py", champion)
    objective_state = repo / "objective_state.json"
    _write(objective_state, {"objectives": [_objective(family, "research_investigation") for family in FAMILIES]})
    kwargs = dict(repo_root=repo, objective_state_path=objective_state,
                  state_path=repo / "state/state.json", private_workspace=repo / "private",
                  policy_path=repo / "data/aion/canonical_runtime/cognitive_route_champion.json",
                  result_path=repo / "results/hexcore_later_confirmed_cognitive_code_improvement.json")
    first = run_once(**kwargs)
    assert first["passed"] is False
    assert first["status"] == "provisional_pending_later_outcome"
    assert first["private_tournament"]["challenger_correct"] == 5
    assert first["private_tournament"]["champion_correct"] == 2
    assert first["private_tournament"]["malicious"]["rejected"] == 6
    policy_id = first["policy"]["policy_id"]
    library = ExecutiveSkillsLibrary(repo / "data/aion/canonical_runtime/executive_skills.json")
    assert library.select_method("construct witness", {"objective_family": "mathematical_reasoning"})["method"] == "learning_apprenticeship"

    rows = [_objective(family, "research_investigation") for family in FAMILIES]
    rows.extend([
        _objective("software_tool", "product_delivery", policy_id=policy_id, confirmed=True),
        _objective("data_decision", "strategic_decision", policy_id=policy_id, confirmed=True),
        _objective("mathematical_reasoning", "learning_apprenticeship", policy_id=policy_id, confirmed=True),
    ])
    _write(objective_state, {"objectives": rows})
    second = run_once(**kwargs)
    assert second["passed"] is True
    assert second["gate"]["later_confirmed_projects"] == 3
    assert second["gate"]["later_distinct_methods"] == 3
    assert second["gate"]["champion_source_preserved"] is True

