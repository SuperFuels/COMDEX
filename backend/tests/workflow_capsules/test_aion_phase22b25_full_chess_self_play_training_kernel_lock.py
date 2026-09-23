from backend.modules.aion_games import run_full_chess_self_play_training_kernel


def test_phase22b25_runs_training_games(tmp_path):
    result = run_full_chess_self_play_training_kernel(
        memory_path=tmp_path / "self_play_training_memory.json"
    )

    assert result.kernel_version == "phase22b25_full_chess_self_play_training_kernel_v1"
    assert result.board_size == 8
    assert result.training_game_count == 4
    assert result.completed_training_game_count == 4
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b25_records_reinforcement_and_penalties(tmp_path):
    result = run_full_chess_self_play_training_kernel(
        memory_path=tmp_path / "self_play_training_memory.json"
    )

    assert result.stable_or_winning_game_count == 2
    assert result.losing_or_penalised_game_count == 2
    assert result.reinforcement_update_count == 2
    assert result.penalty_update_count == 2
    assert result.evidence["reinforces_successful_lines"] is True
    assert result.evidence["penalises_bad_lines"] is True


def test_phase22b25_improves_policy_strength(tmp_path):
    result = run_full_chess_self_play_training_kernel(
        memory_path=tmp_path / "self_play_training_memory.json"
    )

    assert result.final_policy_strength > result.initial_policy_strength
    assert result.policy_improvement_delta > 0
    assert result.selected_policy_after_training == "POLICY-LEARNED"
    assert result.rejected_policy_after_training == "POLICY-KING-RISK"
    assert result.evidence["improves_learned_policy_strength"] is True
    assert result.evidence["selects_learned_policy_after_training"] is True


def test_phase22b25_emits_training_trace_hash(tmp_path):
    result = run_full_chess_self_play_training_kernel(
        memory_path=tmp_path / "self_play_training_memory.json"
    )

    assert len(result.training_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b25_persists_training_memory(tmp_path):
    memory_path = tmp_path / "self_play_training_memory.json"

    first = run_full_chess_self_play_training_kernel(memory_path=memory_path)
    second = run_full_chess_self_play_training_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_training_policy["kernel_run_count"] >= 2
    assert second.final_training_policy["self_play_training_count"] >= 2
    assert second.final_training_policy["training_game_total"] >= 8
    assert second.final_policy_strength > first.final_policy_strength
    assert memory_path.exists()
