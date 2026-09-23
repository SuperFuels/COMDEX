import gzip
import hashlib
import json
from pathlib import Path

import pytest

from backend.modules.hexcore.governed_intelligence_glyph_consolidation import (
    GovernedIntelligenceGlyphStore,
    run,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_verified_intelligence_compresses_without_copying_raw_evidence(tmp_path):
    result = run(
        repo_root=REPO_ROOT, index_path=tmp_path / "glyphs/index.json",
        compressed_path=tmp_path / "glyphs/glyphs.json.gz",
        result_path=tmp_path / "result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["working_memory_reduction"] >= 0.75
    assert result["gate"]["raw_evidence_duplicated"] is False
    assert result["gate"]["source_evidence_deleted"] == 0
    assert result["gate"]["all_provenance_resolves"] is True


def test_curriculum_glyphs_are_not_promoted_as_learned(tmp_path):
    store = GovernedIntelligenceGlyphStore(
        repo_root=REPO_ROOT, index_path=tmp_path / "glyphs/index.json",
        compressed_path=tmp_path / "glyphs/glyphs.json.gz",
    )
    store.build()
    packet = store.load_and_verify()["packet"]
    curricula = [row for row in packet["glyphs"] if row["k"] == "Curriculum"]
    assert curricula
    assert all(row["s"] == "proposed_not_learned" and not row["e"] for row in curricula)
    assert all(row["r"].startswith("⟦ Curriculum") for row in curricula)


def test_glyph_store_fails_closed_when_compressed_packet_is_altered(tmp_path):
    store = GovernedIntelligenceGlyphStore(
        repo_root=REPO_ROOT, index_path=tmp_path / "glyphs/index.json",
        compressed_path=tmp_path / "glyphs/glyphs.json.gz",
    )
    store.build()
    with open(store.compressed_path, "ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        store.load_and_verify()


def test_progressive_evidence_mints_deduplicated_provenance_glyphs(tmp_path):
    artifact = tmp_path / "results/progressive_competency/outcome.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({"passed": True, "checks": 4}), encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    state = {
        "subjects": {"python_core": {"name": "Python Core", "subskills": ["collections"]}},
        "evidence": [
            {"subject_id": "python_core", "kind": "exercise", "subskills": ["collections"],
             "verified": True, "artifact": "results/progressive_competency/outcome.json",
             "artifact_hash": digest},
            {"subject_id": "python_core", "kind": "knowledge_test", "subskills": ["collections"],
             "verified": True, "artifact": "results/progressive_competency/outcome.json",
             "artifact_hash": digest},
        ],
    }
    state_path = tmp_path / "backend/modules/hexcore/data/progressive_competency/state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    store = GovernedIntelligenceGlyphStore(
        repo_root=tmp_path, index_path=tmp_path / "glyphs/index.json",
        compressed_path=tmp_path / "glyphs/glyphs.json.gz",
    )
    index = store.build()
    packet = store.load_and_verify()["packet"]
    names = {(row["k"], row["n"]) for row in packet["glyphs"]}
    assert ("Skill", "competency:python_core") in names
    assert ("Knowledge", "python_core.collections") in names
    assert sum(row["n"] == "python_core.collections" for row in packet["glyphs"]) == 1
    assert index["progressive_evidence_records"] == 2
    assert index["progressive_subjects_consolidated"] == 1
