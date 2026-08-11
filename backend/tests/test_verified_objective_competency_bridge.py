import hashlib
import json
from pathlib import Path

from backend.modules.hexcore.verified_objective_competency_bridge import (
    FAMILY_TO_SUBJECT, run,
)


def test_bridge_revalidates_delayed_artifacts_and_is_idempotent(tmp_path: Path) -> None:
    objectives = []
    for family in FAMILY_TO_SUBJECT:
        for index in range(3):
            artifact = tmp_path / "artifacts" / f"{family}-{index}.txt"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(f"verified {family} {index}", encoding="utf-8")
            objectives.append({
                "objective_id": f"objective_{family}_{index}",
                "family": family,
                "status": "consequence_confirmed",
                "evaluation": {"passed": True, "authority": f"later_{family}"},
                "later_outcome_sha256": f"later-{family}-{index}",
                "commitment_sha256": f"commit-{family}-{index}",
                "authority_delay_seconds": 61,
                "owner_interventions": 0,
                "artifact": {"path": str(artifact),
                             "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()},
            })
    source = tmp_path / "backend/modules/hexcore/data/open_useful_objectives/state.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"objectives": objectives}), encoding="utf-8")
    first = run(repo_root=tmp_path, result_path=tmp_path / "results/bridge.json")
    second = run(repo_root=tmp_path, result_path=tmp_path / "results/bridge.json")
    assert first["passed"] is True
    assert first["gate"]["new_evidence_records"] == 12
    assert first["gate"]["retention_evidence_awarded"] == 0
    assert second["passed"] is True
    assert second["gate"]["new_evidence_records"] == 0
    assert second["gate"]["artifact_hash_checks_passed"] == 12
