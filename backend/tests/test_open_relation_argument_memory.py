from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_open_relation_argument_memory_passes_governed_gate():
    result = json.loads(
        (
            ROOT / "results/hexcore_open_relation_argument_memory.json"
        ).read_text(encoding="utf-8")
    )

    gate = result["gate"]
    assert result["passed"] is True
    assert gate["supplied_relation_types"] == 0
    assert gate["invented_concepts"] >= 50
    assert gate["invented_relations"] >= 40
    assert gate["invented_predicate_types"] >= 30
    assert gate["weakest_book_relations"] >= 5
    assert gate["reported_arguments"] >= 15
    assert gate["predicate_consolidation_coverage"] == 1.0
    assert gate["predicate_compression"] >= 0.2
    assert gate["delayed_memory_queries"] == 12
    assert gate["delayed_memory_accuracy"] == 1.0
    assert gate["source_files_reread_during_delayed_query"] == 0
    assert gate["provenance_completeness"] == 1.0
    assert gate["reported_arguments_marked_verified"] == 0
    assert gate["unsafe_knowledge_commitments"] == 0
    assert result["restart"]["relearning_failures"] == 0


def test_open_relation_memory_preserves_original_and_canonical_predicates():
    result = json.loads(
        (
            ROOT / "results/hexcore_open_relation_argument_memory.json"
        ).read_text(encoding="utf-8")
    )

    assert result["relations"]
    assert all(
        row["predicate"]
        and row["canonical_predicate"]
        and row["evidence_quote"]
        and row["status"] == "reported_by_source"
        for row in result["relations"]
    )
    covered = {
        member
        for cluster in result["predicate_clusters"]
        for member in cluster["members"]
    }
    assert covered == {row["predicate"] for row in result["relations"]}
    assert all(
        row["status"] == "reported_argument"
        for row in result["arguments"]
    )
