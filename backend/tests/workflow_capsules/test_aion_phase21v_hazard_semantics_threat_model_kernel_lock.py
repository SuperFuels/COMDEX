from backend.modules.aion_survival import run_hazard_semantics_threat_model_kernel


def test_phase21v_identifies_multiple_threat_types(tmp_path):
    result = run_hazard_semantics_threat_model_kernel(memory_path=tmp_path / "threat_memory.json")

    assert result.kernel_version == "phase21v_hazard_semantics_threat_model_kernel_v1"
    assert result.threats_identified >= 4
    assert result.immediate_threats >= 1
    assert result.delayed_threats >= 1
    assert result.bait_threats >= 1
    assert result.avoided_semantic_threat is True
    assert result.safe_action == "up"
    assert result.unsafe_action == "right"
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase21v_tracks_danger_targets_and_horizons(tmp_path):
    result = run_hazard_semantics_threat_model_kernel(memory_path=tmp_path / "threat_memory.json")

    targets = set(result.evidence["danger_targets"])
    hazard_types = set(result.evidence["hazard_types"])

    assert "energy" in targets
    assert "future_route" in targets
    assert "future_options" in targets
    assert "survival" in targets

    assert "immediate_damage" in hazard_types
    assert "bait_reward" in hazard_types
    assert "delayed_trap" in hazard_types
    assert "unknown_entity" in hazard_types

    horizons = {t["danger_horizon"] for t in result.threat_models}
    assert max(horizons) >= 3


def test_phase21v_persists_threat_memory(tmp_path):
    memory_path = tmp_path / "threat_memory.json"

    first = run_hazard_semantics_threat_model_kernel(memory_path=memory_path)
    second = run_hazard_semantics_threat_model_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_threat_policy["semantic_avoidance_count"] >= 2
    assert memory_path.exists()
