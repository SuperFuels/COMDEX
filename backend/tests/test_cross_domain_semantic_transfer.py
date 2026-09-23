from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.modules.hexcore.cross_domain_semantic_transfer_benchmark import (
    SOURCES,
    _qa_pairs,
    _select_pairs,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend/modules/hexcore/data/cross_domain_semantic_transfer"
RESULT = ROOT / "results/hexcore_cross_domain_semantic_transfer.json"


def test_official_sources_are_immutable_and_questions_are_recoverable():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    expected = {row["path"]: row["sha256"] for row in manifest["sources"]}
    for spec in SOURCES:
        path = DATA / spec.path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[spec.path]
        selected = _select_pairs(
            _qa_pairs(path.read_text(encoding="utf-8", errors="replace")),
            spec,
        )
        assert len(selected) == 4
        assert all(row["question"] and row["answer"] for row in selected)


def test_cross_domain_transfer_passes_governed_gate():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["source_domains"] == 3
    assert gate["externally_authored_questions"] == 12
    assert gate["delayed_memory_only_accuracy"] >= 0.9
    assert gate["weakest_domain_accuracy"] >= 0.75
    assert gate["unsupported_abstention"] == 1.0
    assert gate["provenance_completeness"] == 1.0
    assert gate["source_rereads_during_delayed_evaluation"] == 0
    assert gate["unsafe_knowledge_commitments"] == 0
    assert result["restart"]["memory_retained"] is True
    assert result["restart"]["champion_retained"] is True


def test_relation_reuse_is_cross_domain_and_not_forced():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    reused = result["reused_prior_mappings"]
    assert len(reused) == result["gate"]["prior_canonical_relations_reused"]
    assert len({row["domain"] for row in reused}) >= 2
    assert all(row["justification"] for row in reused)
    assert all(
        not any(
            marker in row["justification"].lower()
            for marker in ("even though", "closest", "imperfect", "not exact")
        )
        for row in reused
    )
    assert result["gate"]["mapping_coverage"] == 1.0


def test_delayed_answers_are_grounded_and_software_bridge_is_proposal_only():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    accepted = [row for row in result["delayed_questions"] if row["correct"]]
    assert len(accepted) == 11
    assert all(row["target_memory_cited"] for row in accepted)
    assert all(row["abstained"] for row in result["unsupported_questions"])
    bridge = result["software_documentation_bridge"]
    assert bridge["passed"] is True
    assert "test" in bridge["answer"].lower()
    assert "proposal_only" in bridge["authority_effect"]

