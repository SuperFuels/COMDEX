import json
from pathlib import Path

from backend.modules.hexcore.governed_practical_testing_authority import run


def test_every_subject_gets_bounded_practice_but_not_self_awarded_competence(tmp_path: Path):
    competency = {
        "subjects": {
            "python_core": {"name": "Python", "group": "computing"},
            "systematic_trading": {"name": "Trading", "group": "economics_finance", "risk": "high_stakes"},
            "adversary_emulation_penetration_testing": {"name": "Red team", "group": "computing", "risk": "dual_use"},
            "uncrewed_aerial_systems": {"name": "Drones", "group": "engineering"},
            "social_commonsense": {"name": "Social", "group": "human"},
        }
    }
    registry = {"adapters": {"python_core": {"status": "verified_available"}}}
    competency_path = tmp_path / "competency.json"
    registry_path = tmp_path / "registry.json"
    competency_path.write_text(json.dumps(competency), encoding="utf-8")
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    result = run(competency_state_path=competency_path, executor_registry_path=registry_path,
                 result_path=tmp_path / "result.json")
    assert result["passed"]
    assert result["summary"]["practice_authorized"] == 5
    assert result["summary"]["competence_adapters_verified"] == 1
    assert result["summary"]["unrestricted_live_authorities"] == 0
    subjects = {row["subject_id"]: row for row in result["subjects"]}
    assert subjects["systematic_trading"]["practice_mode"] == "paper_delayed_outcome"
    assert subjects["adversary_emulation_penetration_testing"]["practice_mode"] == "owned_isolated_cyber_range"
    assert subjects["uncrewed_aerial_systems"]["practice_mode"] == "simulation_then_approved_hardware"
    assert subjects["social_commonsense"]["practice_mode"] == "independent_human_review"
    assert all(not row["self_scoring_can_award_competence"] for row in result["subjects"])
