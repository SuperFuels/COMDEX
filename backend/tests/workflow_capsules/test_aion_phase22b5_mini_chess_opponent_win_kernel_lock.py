from backend.modules.aion_games import run_mini_chess_opponent_win_kernel


def test_phase22b5_aion_beats_simple_opponent(tmp_path):
    result = run_mini_chess_opponent_win_kernel(memory_path=tmp_path / "opponent_memory.json")

    assert result.kernel_version == "phase22b5_mini_chess_opponent_win_kernel_v1"
    assert result.opponent_type == "deterministic_weak_mini_chess_opponent_v1"
    assert result.aion_won is True
    assert result.opponent_defeated is True
    assert result.win_condition == "mini_chess_mate_net"
    assert result.aion_legal_moves > 0
    assert result.aion_illegal_moves == 0
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b5_applies_learned_policy_and_avoids_traps(tmp_path):
    result = run_mini_chess_opponent_win_kernel(memory_path=tmp_path / "opponent_memory.json")

    assert result.learned_policy_applied is True
    assert result.avoided_known_bad_capture is True
    assert result.preserved_king_safety is True
    assert result.traps_avoided >= 3
    assert result.material_score_delta > 0
    assert result.evidence["uses_safe_capture_policy"] is True
    assert result.evidence["uses_threat_map_policy"] is True
    assert result.evidence["uses_self_play_policy"] is True


def test_phase22b5_persists_opponent_win_memory(tmp_path):
    memory_path = tmp_path / "opponent_memory.json"

    first = run_mini_chess_opponent_win_kernel(memory_path=memory_path)
    second = run_mini_chess_opponent_win_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_opponent_win_policy["kernel_run_count"] >= 2
    assert second.final_opponent_win_policy["opponent_games_played"] >= 2
    assert second.final_opponent_win_policy["opponent_wins"] >= 2
    assert second.final_opponent_win_policy["learned_policy_application_count"] >= 2
    assert memory_path.exists()
