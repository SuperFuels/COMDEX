from pathlib import Path

from backend.modules.hexcore.progressive_competency_executor import RUNNERS
from backend.modules.hexcore.progressive_outcome_authority_fabric import (
    ProgressiveOutcomeAuthorityFabric,
)


def test_four_authority_families_qualify_six_subject_adapters(tmp_path: Path):
    fabric = ProgressiveOutcomeAuthorityFabric(state_path=tmp_path / "fabric.json")
    available = {sid for sid, row in fabric.state["adapters"].items()
                 if row["status"] == "verified_available"}
    assert available == {
        "mathematics", "english", "research_communication",
        "scientific_method", "data_statistics", "machine_learning_ai",
    }
    assert {row["family"] for row in fabric.state["adapters"].values()} == {
        "proof_and_calculation", "document_and_delayed_question",
        "empirical_dataset_or_experiment", "data_and_statistical_outcome",
        "code_and_system_execution",
    }
    assert all(row["counterexamples_rejected"] == row["counterexamples_total"]
               for row in fabric.state["adapters"].values())


def test_family_adapter_executes_requested_subskill_and_rejects_counterexample(tmp_path: Path):
    fabric = ProgressiveOutcomeAuthorityFabric(state_path=tmp_path / "fabric.json")
    cases = {
        "mathematics": "proof",
        "english": "ambiguity",
        "research_communication": "citation",
        "scientific_method": "causal_inference",
        "data_statistics": "time_series",
        "machine_learning_ai": "evaluation",
    }
    for subject_id, skill in cases.items():
        result = fabric.run(subject_id, {
            "requirement": {"kind": "knowledge_test", "subskills": [skill]}
        }, [])
        assert result["passed"] is True
        assert result["gate"]["counterexamples_rejected"] == 1
        assert result["gate"]["unsafe_variants_rejected"] == 6


def test_verified_family_adapters_are_installed_in_progressive_runtime():
    for subject_id in (
        "mathematics", "english", "research_communication",
        "scientific_method", "data_statistics", "machine_learning_ai",
    ):
        assert subject_id in RUNNERS
