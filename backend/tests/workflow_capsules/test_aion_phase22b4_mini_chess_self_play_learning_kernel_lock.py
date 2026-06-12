from backend.modules.aion_games import run_mini_chess_self_play_learning_kernel


def test_phase22b4_self_play_improves_from_loss_to_win(tmp_path):
    result = run_mini_chess_self_play_learning_kernel(memory_path=tmp_path / "self_play_memory.json")

    assert result.kernel_version == "phase22b4_mini_chess_self_play_learning_kernel_v1"
    assert result.episodes_run == 4
    assert result.baseline_result == "loss"
    assert result.final_result == "win"
    assert result.reward_delta > 0
    assert result.policy_improved is True
    assert result.win_condition_reached is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b4_learns_from_bad_capture_and_preserves_king_safety(tmp_path):
    result = run_mini_chess_self_play_learning_kernel(memory_path=tmp_path / "self_play_memory.json")

    assert result.learned_from_loss is True
    assert result.avoided_repeated_bad_capture is True
    assert any(ep["unsafe_capture"] is True for ep in result.episodes)
    assert any(ep["king_safe"] is True and ep["result"] == "win" for ep in result.episodes)
    assert result.evidence["uses_bad_capture_avoidance"] is True
    assert result.evidence["uses_king_safety_priority"] is True


def test_phase22b4_persists_self_play_memory(tmp_path):
    memory_path = tmp_path / "self_play_memory.json"

    first = run_mini_chess_self_play_learning_kernel(memory_path=memory_path)
    second = run_mini_chess_self_play_learning_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_self_play_policy["kernel_run_count"] >= 2
    assert second.final_self_play_policy["self_play_game_count"] >= 8
    assert second.final_self_play_policy["wins"] >= 2
    assert second.final_self_play_policy["learned_from_loss_count"] >= 2
    assert memory_path.exists()
