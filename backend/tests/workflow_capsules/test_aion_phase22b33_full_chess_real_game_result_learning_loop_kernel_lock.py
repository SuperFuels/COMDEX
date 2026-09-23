from backend.modules.aion_games import run_full_chess_real_game_result_learning_loop_kernel


def test_phase22b33_ingests_real_game_results_without_human_approval(tmp_path):
    result = run_full_chess_real_game_result_learning_loop_kernel(
        memory_path=tmp_path / "real_game_learning_memory.json"
    )

    assert result.kernel_version == "phase22b33_full_chess_real_game_result_learning_loop_kernel_v1"
    assert result.human_approval_required is False
    assert result.real_game_result_count == 4
    assert result.completed_game_count == 4
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b33_records_results(tmp_path):
    result = run_full_chess_real_game_result_learning_loop_kernel(
        memory_path=tmp_path / "real_game_learning_memory.json"
    )

    assert result.win_count == 2
    assert result.draw_count == 1
    assert result.loss_count == 1
    assert result.evidence["records_wins"] is True
    assert result.evidence["records_draws"] is True
    assert result.evidence["records_losses"] is True


def test_phase22b33_updates_learning_policy(tmp_path):
    result = run_full_chess_real_game_result_learning_loop_kernel(
        memory_path=tmp_path / "real_game_learning_memory.json"
    )

    assert result.reinforcement_update_count == 3
    assert result.penalty_update_count == 1
    assert result.final_strategy_strength > result.initial_strategy_strength
    assert result.strategy_improvement_delta > 0
    assert result.preferred_policy_after_learning == "AUTONOMOUS-LEARNED-SAFE-CAPTURE"
    assert result.penalised_policy_after_learning == "AUTONOMOUS-GREEDY-QUEEN"


def test_phase22b33_emits_trace_hash(tmp_path):
    result = run_full_chess_real_game_result_learning_loop_kernel(
        memory_path=tmp_path / "real_game_learning_memory.json"
    )

    assert len(result.real_game_learning_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b33_persists_real_game_learning_memory(tmp_path):
    memory_path = tmp_path / "real_game_learning_memory.json"

    first = run_full_chess_real_game_result_learning_loop_kernel(memory_path=memory_path)
    second = run_full_chess_real_game_result_learning_loop_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_real_game_learning_policy["kernel_run_count"] >= 2
    assert second.final_real_game_learning_policy["real_game_learning_session_count"] >= 2
    assert second.final_real_game_learning_policy["real_game_total"] >= 8
    assert second.final_real_game_learning_policy["strategy_strength"] > first.final_strategy_strength
    assert memory_path.exists()
