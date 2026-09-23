from pathlib import Path

from backend.modules.hexcore.persistent_natural_language_mission_interface import (
    PersistentDiscourseManager,
    SemanticIntentModel,
    run,
)


def _model() -> SemanticIntentModel:
    return SemanticIntentModel(Path("backend/models/all-MiniLM-L6-v2"))


def test_discourse_manager_clarifies_multiple_referents(tmp_path: Path):
    manager = PersistentDiscourseManager(tmp_path / "state.json", _model())
    result = manager.interpret("ambiguous", ['We discussed "alpha" and "beta".', "Repair it."])
    assert result["status"] == "clarification_required"
    assert result["reason"] == "multiple_referents"


def test_discourse_manager_preserves_correction_and_audience(tmp_path: Path):
    manager = PersistentDiscourseManager(tmp_path / "state.json", _model())
    corrected = manager.interpret("correction", ['Monitor "weather feed".', 'Actually I meant "release feed". Keep watching it for changes.'])
    explained = manager.interpret("audience", ['The subject is "causal inference".', "Walk a beginner through the concept."])
    assert corrected["intent"] == "monitor"
    assert corrected["target"] == "release feed"
    assert explained["explanation_contract"] == "plain_language_with_example"


def test_persistent_natural_language_interface_compiles_and_retains(tmp_path: Path):
    result = run(workspace_root=tmp_path / "campaign", result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["semantic_intent_accuracy"] == 1.0
    assert result["gate"]["verified_interpretations"] == 10
    assert result["gate"]["ambiguity_abstention"] is True
    assert result["gate"]["correction_retained"] is True
    assert result["gate"]["unsafe_goal_compilations"] == 0
    assert result["restart"]["relearning_turns"] == 0
