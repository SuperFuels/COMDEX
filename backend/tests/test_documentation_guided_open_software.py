from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "results/hexcore_documentation_guided_open_software.json"
V2 = ROOT / "results/hexcore_source_grounded_software_memory.json"


def test_documentation_guided_open_software_is_promoted():
    result = json.loads(V1.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert result["passed"] is True
    assert gate["accepted"] is True
    assert gate["repositories"] == 3
    assert gate["control_success"] == 1.0
    assert gate["memory_challenger_success"] == 1.0
    assert gate["weakest_repository_success"] == 1.0
    assert gate["control_attempts"] == 5
    assert gate["memory_challenger_attempts"] == 4
    assert gate["attempt_reduction"] == 0.2
    assert result["restart"]["champion_retained"] is True


def test_repository_ontologies_are_open_and_provenance_grounded():
    result = json.loads(V1.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert gate["open_repository_ontologies"] == 3
    assert gate["invented_concepts"] >= 12
    assert gate["grounded_relations"] >= 12
    assert gate["code_bindings_confirmed_by_source"] >= 6
    assert gate["provenance_completeness"] == 1.0
    assert all(
        row.get("evidence_quote") and row.get("document_hash")
        for ontology in result["ontologies"].values()
        for family in ("concepts", "relations", "invariants", "bindings")
        for row in ontology[family]
    )


def test_accepted_repairs_have_test_specs_and_security_is_fail_closed():
    result = json.loads(V1.read_text(encoding="utf-8"))
    assert result["gate"]["accepted_with_functional_test_specifications"] == 3
    assert result["gate"]["accepted_with_security_test_specifications"] == 3
    assert result["security_audit"]["passed"] is True
    assert result["security_audit"]["blocked"] == 6
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["gate"]["live_sources_unchanged"] is True


def test_unselective_source_grounding_is_rejected_without_harming_champion():
    result = json.loads(V2.read_text(encoding="utf-8"))
    gate = result["gate"]
    assert result["passed"] is False
    assert gate["accepted"] is False
    assert gate["control_success"] == 1.0
    assert gate["grounded_memory_success"] == 2 / 3
    assert gate["grounded_memory_attempts"] > gate["control_attempts"]
    assert "repair" in gate["errors"]
    assert "lift" in gate["errors"]
    assert result["promotion"]["decision"]["promoted"] is False
    assert result["restart"]["session_retained"] is True

