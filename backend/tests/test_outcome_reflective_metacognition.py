from backend.modules.hexcore.outcome_reflective_metacognition_benchmark import run


def test_outcome_reflection_attributes_and_transfers_scoped_lessons(tmp_path):
    result = run(
        state_path=tmp_path / "state.json",
        result_path=tmp_path / "result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["attribution_accuracy"] == 1.0
    assert result["gate"]["matching_lesson_transfer"] == 1.0
    assert result["gate"]["unrelated_cheap_preservation"] == 1.0
    assert result["gate"]["routine_success_noop"] is True
    assert result["gate"]["llm_calls"] == 0
