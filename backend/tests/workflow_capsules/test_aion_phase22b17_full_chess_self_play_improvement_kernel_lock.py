from backend.modules.aion_games import run_full_chess_self_play_improvement_kernel


def test_phase22b17_runs_self_play_episodes(tmp_path):
    result = run_full_chess_self_play_improvement_kernel(memory_path=tmp_path / "self_play_memory.json")

    assert result.kernel_version == "phase22b17_full_chess_self_play_improvement_kernel_v1"
    assert result.board_size == 8
    assert result.self_play_episode_count == 4
    assert result.completed_episode_count == 4
    assert result.stable_or_winning_episode_count == 4
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b17_improves_policy_weights(tmp_path):
    result = run_full_chess_self_play_improvement_kernel(memory_path=tmp_path / "self_play_memory.json")

    assert result.final_safe_capture_weight > result.initial_safe_capture_weight
    assert result.final_multi_ply_survival_weight > result.initial_multi_ply_survival_weight
    assert result.improved_episode_count == result.self_play_episode_count
    assert result.evidence["improves_policy_weights"] is True


def test_phase22b17_increases_bad_line_penalties(tmp_path):
    result = run_full_chess_self_play_improvement_kernel(memory_path=tmp_path / "self_play_memory.json")

    assert result.final_greedy_capture_penalty > result.initial_greedy_capture_penalty
    assert result.final_king_exposure_penalty > result.initial_king_exposure_penalty
    assert result.final_material_loss_penalty > result.initial_material_loss_penalty
    assert result.evidence["increases_bad_line_penalties"] is True


def test_phase22b17_retains_preferred_strategy_and_avoids_bad_line(tmp_path):
    result = run_full_chess_self_play_improvement_kernel(memory_path=tmp_path / "self_play_memory.json")

    assert result.preferred_strategy_after_self_play == "STRAT-1 / LINE-1"
    assert result.avoided_strategy_after_self_play == "STRAT-2 greedy queen capture"
    assert result.preferred_strategy_retention_count == result.self_play_episode_count
    assert result.avoided_bad_line_count == result.self_play_episode_count
    assert result.evidence["retains_preferred_strategy"] is True
    assert result.evidence["avoids_bad_strategy"] is True
    assert len(result.self_play_trace_hash) == 64


def test_phase22b17_persists_self_play_memory(tmp_path):
    memory_path = tmp_path / "self_play_memory.json"

    first = run_full_chess_self_play_improvement_kernel(memory_path=memory_path)
    second = run_full_chess_self_play_improvement_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_self_play_policy["kernel_run_count"] >= 2
    assert second.final_self_play_policy["self_play_loop_count"] >= 2
    assert second.final_safe_capture_weight > first.final_safe_capture_weight
    assert second.final_greedy_capture_penalty > first.final_greedy_capture_penalty
    assert memory_path.exists()
