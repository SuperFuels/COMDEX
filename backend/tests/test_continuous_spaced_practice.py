import json
from pathlib import Path

from backend.modules.hexcore.continuous_spaced_practice import run


def test_spaced_practice_rotates_and_never_awards_competence(tmp_path: Path):
    competency = {
        "subjects": {
            "alpha": {"name": "Alpha", "subskills": ["a", "b"]},
            "beta": {"name": "Beta", "subskills": ["x"]},
        },
        "evidence": [],
    }
    competency_path = tmp_path / "competency.json"
    competency_path.write_text(json.dumps(competency), encoding="utf-8")

    def runner(contract, evidence):
        return {"passed": True, "authority_boundary": "test sandbox"}

    arguments = dict(
        repo_root=tmp_path, competency_state_path=competency_path,
        state_path=tmp_path / "state.json", result_path=tmp_path / "result.json",
        minimum_interval_seconds=10, runners={"alpha": runner, "beta": runner},
    )
    first = run(**arguments, now=100)
    waiting = run(**arguments, now=105)
    second = run(**arguments, now=111)
    assert first["latest"]["subject_id"] == "alpha"
    assert waiting["status"] == "waiting_for_practice_cadence"
    assert second["latest"]["subject_id"] == "beta"
    assert first["latest"]["awards_competence"] is False
    assert second["summary"]["total_rehearsals"] == 2


def test_uncovered_subject_gets_preparatory_practice_without_false_competence(tmp_path: Path):
    competency = {
        "subjects": {
            "covered": {"name": "Covered", "subskills": ["execute"]},
            "uncovered": {"name": "Uncovered", "subskills": ["analyse"]},
        },
        "evidence": [],
    }
    competency_path = tmp_path / "competency.json"
    competency_path.write_text(json.dumps(competency), encoding="utf-8")

    def runner(contract, evidence):
        return {"passed": True, "authority_boundary": "verified practice"}

    arguments = dict(
        repo_root=tmp_path, competency_state_path=competency_path,
        state_path=tmp_path / "state.json", result_path=tmp_path / "result.json",
        minimum_interval_seconds=1, runners={"covered": runner},
    )
    run(**arguments, now=100)
    second = run(**arguments, now=102)
    assert second["latest"]["subject_id"] == "uncovered"
    assert second["latest"]["practice_mode"] == "preparatory_non_promotional"
    assert second["latest"]["awards_competence"] is False
    assert second["summary"]["subjects_with_practice_paths"] == 2
    assert second["summary"]["subjects_with_verified_practice_adapters"] == 1
    assert second["summary"]["diagnostic_only_subjects"] == 1
    assert json.loads(competency_path.read_text())["evidence"] == []
