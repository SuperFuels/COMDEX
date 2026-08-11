import json
import shutil
from pathlib import Path

from backend.modules.hexcore.autonomous_functional_glyph_induction import run


ROOT = Path(__file__).resolve().parents[2]


def test_verified_trajectories_expand_functional_memory_without_awarding_levels(tmp_path: Path) -> None:
    store = tmp_path / "lexicon.json.gz"
    shutil.copy2(ROOT / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz", store)
    result = run(
        repo_root=ROOT, store_path=store,
        capsule_dir=ROOT / "backend/modules/hexcore/data/functional_mastery_memory/capsules",
        reconstruction_result_path=ROOT / "results/hexcore_functional_mastery_memory.json",
        result_path=tmp_path / "result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["verified_trajectories_induced"] >= 6
    assert result["gate"]["induced_procedures_reconstructed"] >= 6
    assert result["gate"]["cross_domain_compositions_passed"] == 2
    assert result["gate"]["content_idempotent"] is True
    assert result["gate"]["competency_awards"] == 0
    assert result["gate"]["raw_answers_stored"] == 0


def test_all_induced_capsules_have_corruption_and_provenance_controls(tmp_path: Path) -> None:
    store = tmp_path / "lexicon.json.gz"
    shutil.copy2(ROOT / "backend/modules/hexcore/data/functional_glyph_lexicon/lexicon.json.gz", store)
    result = run(
        repo_root=ROOT, store_path=store,
        capsule_dir=ROOT / "backend/modules/hexcore/data/functional_mastery_memory/capsules",
        reconstruction_result_path=ROOT / "results/hexcore_functional_mastery_memory.json",
        result_path=tmp_path / "result.json",
    )
    assert result["gate"]["corrupted_capsules_rejected"] == result["gate"]["verified_trajectories_induced"]
    assert result["gate"]["evidence_resolves"] is True
    assert result["gate"]["node_provenance_resolves"] is True
    assert len(result["memory_qualified_competencies"]) >= 6
    assert {row["level"] for row in result["memory_qualified_competencies"]} <= {"advanced", "expert"}
