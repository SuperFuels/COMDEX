from backend.modules.aion_games import run_full_chess_autonomous_bot_learning_policy_kernel


def test_phase22b32_enables_autonomous_mode_without_human_approval(tmp_path):
    result = run_full_chess_autonomous_bot_learning_policy_kernel(
        memory_path=tmp_path / "autonomous_learning_memory.json"
    )

    assert result.kernel_version == "phase22b32_full_chess_autonomous_bot_learning_policy_kernel_v1"
    assert result.autonomous_mode_enabled is True
    assert result.human_approval_required is False
    assert result.legal_move_required is True
    assert result.network_guard_required is True
    assert result.token_guard_required is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b32_selects_bestmove_and_policy(tmp_path):
    result = run_full_chess_autonomous_bot_learning_policy_kernel(
        memory_path=tmp_path / "autonomous_learning_memory.json"
    )

    assert result.selected_bestmove == "c4d5"
    assert result.selected_policy == "AUTONOMOUS-LEARNED-SAFE-CAPTURE"
    assert result.evidence["selects_bestmove"] is True
    assert result.evidence["keeps_legal_move_guard"] is True


def test_phase22b32_records_learning_and_updates_strategy(tmp_path):
    result = run_full_chess_autonomous_bot_learning_policy_kernel(
        memory_path=tmp_path / "autonomous_learning_memory.json"
    )

    assert result.learning_game_count == 4
    assert result.completed_learning_game_count == 4
    assert result.win_or_stable_count == 3
    assert result.loss_or_penalty_count == 1
    assert result.reinforcement_update_count == 3
    assert result.penalty_update_count == 1
    assert result.strategy_improvement_delta > 0
    assert result.final_strategy_strength > result.initial_strategy_strength


def test_phase22b32_emits_trace_hash(tmp_path):
    result = run_full_chess_autonomous_bot_learning_policy_kernel(
        memory_path=tmp_path / "autonomous_learning_memory.json"
    )

    assert len(result.autonomous_learning_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b32_persists_autonomous_learning_memory(tmp_path):
    memory_path = tmp_path / "autonomous_learning_memory.json"

    first = run_full_chess_autonomous_bot_learning_policy_kernel(memory_path=memory_path)
    second = run_full_chess_autonomous_bot_learning_policy_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_autonomous_learning_policy["kernel_run_count"] >= 2
    assert second.final_autonomous_learning_policy["autonomous_learning_session_count"] >= 2
    assert second.final_autonomous_learning_policy["learning_game_total"] >= 8
    assert second.final_autonomous_learning_policy["strategy_strength"] > first.final_strategy_strength
    assert memory_path.exists()
