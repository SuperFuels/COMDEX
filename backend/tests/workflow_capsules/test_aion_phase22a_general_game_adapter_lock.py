from backend.modules.aion_games import run_general_game_adapter


def test_phase22a_adapts_multiple_game_types(tmp_path):
    result = run_general_game_adapter(memory_path=tmp_path / "adapter_memory.json")

    assert result.adapter_version == "phase22a_general_game_adapter_v1"
    assert result.games_adapted == 3
    assert result.survival_adapter_passed is True
    assert result.chess_adapter_passed is True
    assert result.real_world_adapter_passed is True
    assert set(result.adapted_game_types) == {
        "survival_grid",
        "chess_like",
        "real_world_task",
    }
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22a_common_contract_keys_exist_for_each_game(tmp_path):
    result = run_general_game_adapter(memory_path=tmp_path / "adapter_memory.json")

    required = set(result.common_contract_keys)
    for state in result.adapted_states:
        assert required.issubset(set(state.keys()))
        assert state["goals"]
        assert state["legal_actions"]
        assert state["threats"]
        assert "risk_confidence" in state["uncertainty"]
        assert len(state["adapter_trace_hash"]) == 64


def test_phase22a_chess_like_adapter_contains_tactical_and_delayed_threats(tmp_path):
    result = run_general_game_adapter(memory_path=tmp_path / "adapter_memory.json")
    chess = next(s for s in result.adapted_states if s["game_type"] == "chess_like")

    threat_types = {t["threat_type"] for t in chess["threats"]}
    risk_tags = {tag for action in chess["legal_actions"] for tag in action["risk_tags"]}

    assert "tactical_threat" in threat_types
    assert "delayed_trap" in threat_types
    assert "mate_in_six_risk" in risk_tags
    assert "bait_reward" in risk_tags


def test_phase22a_persists_adapter_memory(tmp_path):
    memory_path = tmp_path / "adapter_memory.json"

    first = run_general_game_adapter(memory_path=memory_path)
    second = run_general_game_adapter(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_adapter_policy["adapter_run_count"] >= 2
    assert second.final_adapter_policy["successful_adapter_count"] >= 2
    assert memory_path.exists()
