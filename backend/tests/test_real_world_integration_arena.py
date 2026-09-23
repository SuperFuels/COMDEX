import json
from datetime import datetime, timezone
from pathlib import Path

import backend.modules.hexcore.real_world_integration_arena as arena_module
from backend.modules.hexcore.real_world_integration_arena import run_cycle


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _progress(level: str = "advanced") -> dict:
    subject_ids = {
        "algorithms_data_structures", "integrated_engineering_capstone",
        "networking", "distributed_systems", "architecture_operations", "cloud_devops_sre",
        "software_engineering", "python_core",
    }
    return {"subjects": {
        subject_id: {"subject_id": subject_id, "name": subject_id.replace("_", " ").title(),
                     "overall_level": level, "evidence_records": 12}
        for subject_id in subject_ids
    }}


def test_arena_runs_parallel_capsule_without_awarding_competence(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/aion_progressive_competency_status.json"
    progress = _progress()
    _write(progress_path, progress)
    result = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    assert result["passed"] is True
    assert result["parallel_to_curriculum"] is True
    assert result["awards_subject_competence"] is False
    capsule = result["latest_capsule"]
    assert capsule["baseline"]["evaluation"]["passed"] is False
    assert capsule["fresh_retry"]["evaluation"]["passed"] is True
    assert capsule["adversarial_probe"]["correctly_rejected"] is True
    assert capsule["unsafe_actions"] == 0
    assert json.loads(progress_path.read_text(encoding="utf-8")) == progress


def test_arena_advances_without_duplicate_capsules(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/aion_progressive_competency_status.json"
    _write(progress_path, _progress())
    first = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    second = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    third = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    fourth = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    assert len({first["latest_capsule"]["mission_id"], second["latest_capsule"]["mission_id"],
                third["latest_capsule"]["mission_id"]}) == 3
    assert third["capsule_count"] == 3
    assert fourth["status"] == "waiting_for_real_world_eligibility_or_authority"
    assert fourth["latest_capsule"] == {}
    capsule_files = list((tmp_path / "backend/modules/hexcore/data/real_world_integration_arena/capsules").glob("*.json"))
    assert len(capsule_files) == 3


def test_arena_waits_until_subject_bundle_is_learned(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/aion_progressive_competency_status.json"
    _write(progress_path, _progress(level="intermediate"))
    result = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    assert result["status"] == "waiting_for_real_world_eligibility_or_authority"
    assert result["eligible_missions"] == []
    assert result["capsule_count"] == 0
    assert result["unsafe_actions"] == 0


def test_applied_graph_links_knowledge_gap_repair_and_wisdom(tmp_path: Path) -> None:
    progress_path = tmp_path / "results/aion_progressive_competency_status.json"
    _write(progress_path, _progress())
    result = run_cycle(repo_root=tmp_path, progress_path=progress_path)
    graph = json.loads(Path(result["graph"]["path"]).read_text(encoding="utf-8"))
    relations = {row["relation"] for row in graph["edges"]}
    assert {"APPLIES_IN", "EXPOSES_GAP", "REPAIRED_BY", "VALIDATED_BY",
            "PRODUCES_WISDOM"} <= relations
    assert graph["separate_from_textbook_graph"] is True


def test_later_independent_public_observation_creates_real_capsule(
        tmp_path: Path, monkeypatch) -> None:
    progress_path = tmp_path / "results/aion_progressive_competency_status.json"
    outcome_path = tmp_path / "results/public_outcomes.jsonl"
    _write(progress_path, _progress())
    base = 100_000.0
    monkeypatch.setattr(arena_module.time, "time", lambda: base)

    def observation(cycle: int, epoch: float, revisions: tuple[str, str, str]) -> dict:
        python_revision, node_revision, numpy_version = revisions
        return {
            "cycle": cycle,
            "observed_at": datetime.fromtimestamp(epoch, timezone.utc).isoformat(),
            "outcome_sha256": f"outcome_{cycle}",
            "outcomes": {
                "cpython": {"reachable": True, "revision": python_revision,
                            "authority": "https://github.com/python/cpython.git",
                            "family": "public_source_control"},
                "node": {"reachable": True, "revision": node_revision,
                         "authority": "https://github.com/nodejs/node.git",
                         "family": "public_source_control"},
                "numpy_release": {"reachable": True, "value": numpy_version,
                                  "authority": "https://pypi.org/pypi/numpy/json",
                                  "family": "public_package_registry"},
            },
        }

    outcome_path.parent.mkdir(parents=True, exist_ok=True)
    outcome_path.write_text(json.dumps(observation(1, base - 100, ("py1", "node1", "np1"))) + "\n",
                            encoding="utf-8")
    for _ in range(3):
        run_cycle(repo_root=tmp_path, progress_path=progress_path,
                  public_outcome_ledger=outcome_path)
    pending = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                        public_outcome_ledger=outcome_path, real_world_delay_seconds=60)
    assert pending["status"] == "waiting_for_later_independent_world_observation"
    assert pending["real_world_capsule_count"] == 0
    assert pending["real_world_commitment_integrity"] is True

    with outcome_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observation(2, base + 61, ("py1", "node2", "np1"))) + "\n")
    monkeypatch.setattr(arena_module.time, "time", lambda: base + 61)
    closed = run_cycle(repo_root=tmp_path, progress_path=progress_path,
                       public_outcome_ledger=outcome_path)
    capsule = closed["latest_real_world_capsule"]
    assert closed["status"] == "independent_real_world_outcome_recorded"
    assert closed["real_world_capsule_count"] == 1
    assert capsule["verified_real_outcome"] is True
    assert capsule["outcome_success"] is False
    assert capsule["correct_predictions"] == 2
    assert capsule["scored_predictions"] == 3
    assert capsule["world_model_update_required"] is True
    assert capsule["external_writes"] == 0
    graph = json.loads(Path(closed["graph"]["path"]).read_text(encoding="utf-8"))
    assert "TESTED_IN_REAL_WORLD_BY" in {row["relation"] for row in graph["edges"]}
