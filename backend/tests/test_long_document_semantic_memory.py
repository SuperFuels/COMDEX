from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_long_document_semantic_memory_is_grounded_and_persistent():
    result = json.loads(
        (
            ROOT / "results/hexcore_long_document_semantic_memory.json"
        ).read_text(encoding="utf-8")
    )

    assert result["passed"] is True
    assert result["gate"]["books"] == 3
    assert result["gate"]["source_words"] >= 140_000
    assert result["gate"]["question_accuracy"] >= 8 / 9
    assert result["gate"]["weakest_book_accuracy"] >= 2 / 3
    assert result["gate"]["exact_provenance"] == 1.0
    assert result["gate"]["concept_composition_accuracy"] == 1.0
    assert result["gate"]["hypotheticals_committed_as_facts"] == 0
    assert result["gate"]["contradiction_preserved"] is True
    assert result["gate"]["reported_equals_verified"] is False
    assert result["gate"]["unsafe_knowledge_commitments"] == 0
    assert result["restart"]["delayed_relation_accuracy"] == 1.0
    assert result["restart"]["relearning_failures"] == 0

    relations = {
        (row["subject"], row["relation"], row["value"])
        for row in result["relation_graph"]
    }
    assert ("rabbit", "colour", "white") in relations
    assert ("eyes", "colour", "pink") in relations
    assert ("rabbit", "colour", "pink") not in relations
    assert all(
        row["status"] == "hypothetical_composition"
        and row["committed_as_source_fact"] is False
        for row in result["compositions"]
    )


def test_long_document_source_hashes_are_retained_after_restart():
    result = json.loads(
        (
            ROOT / "results/hexcore_long_document_semantic_memory.json"
        ).read_text(encoding="utf-8")
    )
    state = json.loads(
        (
            ROOT
            / "backend/modules/hexcore/data/"
            "long_document_semantic_memory_state.json"
        ).read_text(encoding="utf-8")
    )

    memories = state["long_document_semantic_memories"]
    assert memories
    assert result["restart"]["book_hashes_retained"] is True
    assert result["restart"]["concepts_retained"] is True
    assert result["restart"]["contradiction_retained"] is True
    assert (
        state["champions"]["long_document_semantic_memory"]
        == "procedure_long_document_semantic_memory_6d1736d5906a"
    )
