from pathlib import Path

from backend.modules.aion_self_improvement.persistent_self_improvement_memory import (
    AionPersistentSelfImprovementMemory,
    run_persistent_self_improvement,
)


def test_phase21k_persistent_memory_saves_and_loads_strategy(tmp_path):
    memory_path = tmp_path / "persistent_strategy_memory.json"

    first = run_persistent_self_improvement(memory_path=memory_path, max_rounds=6)
    assert first.persistence_version == "phase21k_persistent_self_improvement_memory_v1"
    assert first.memory_loaded is False
    assert first.after_known_mapping_count >= 7
    assert first.evidence["uses_llm_shortcut"] is False
    assert memory_path.exists()

    memory = AionPersistentSelfImprovementMemory(memory_path)
    loaded = memory.load()

    assert loaded is not None
    assert loaded.run_count == 1
    assert loaded.best_score == 1.0
    assert loaded.learned_prompt_map["select shape"] == "■"


def test_phase21k_second_run_bootstraps_from_persistent_memory(tmp_path):
    memory_path = tmp_path / "persistent_strategy_memory.json"

    first = run_persistent_self_improvement(memory_path=memory_path, max_rounds=6)
    second = run_persistent_self_improvement(memory_path=memory_path, max_rounds=6)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.before_known_mapping_count >= 7
    assert second.baseline_score == 1.0
    assert second.final_score == 1.0
    assert second.record["run_count"] == 2
    assert second.record["misses"]["select shape"] == 1
    assert second.evidence["starts_from_previous_strategy"] is True


def test_phase21k_persistent_result_serializes(tmp_path):
    memory_path = tmp_path / "persistent_strategy_memory.json"

    result = run_persistent_self_improvement(memory_path=memory_path, max_rounds=4)
    data = result.to_dict()

    assert data["persistence_version"] == "phase21k_persistent_self_improvement_memory_v1"
    assert isinstance(data["record"], dict)
    assert isinstance(data["loop_result"], dict)
    assert data["evidence"]["uses_persistent_memory"] is True
