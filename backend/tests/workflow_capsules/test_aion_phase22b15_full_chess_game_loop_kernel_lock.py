from backend.modules.aion_games import run_full_chess_game_loop_kernel


def test_phase22b15_completes_deterministic_game_loop(tmp_path):
    result = run_full_chess_game_loop_kernel(memory_path=tmp_path / "game_loop_memory.json")

    assert result.kernel_version == "phase22b15_full_chess_game_loop_kernel_v1"
    assert result.board_size == 8
    assert result.planned_turn_count == 6
    assert result.completed_turn_count == 6
    assert result.aion_turn_count == 3
    assert result.opponent_turn_count == 3
    assert result.game_loop_completed is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b15_preserves_legality_and_king_safety(tmp_path):
    result = run_full_chess_game_loop_kernel(memory_path=tmp_path / "game_loop_memory.json")

    assert result.legal_turn_count == result.completed_turn_count
    assert result.king_safe_turn_count == result.completed_turn_count
    assert result.no_illegal_moves_used is True
    assert result.no_king_exposure_allowed is True
    assert result.evidence["uses_legal_move_filter"] is True
    assert result.evidence["uses_king_safety_filter"] is True


def test_phase22b15_uses_reply_and_multi_ply_stack(tmp_path):
    result = run_full_chess_game_loop_kernel(memory_path=tmp_path / "game_loop_memory.json")

    assert result.opponent_reply_evaluated_count >= 3
    assert result.multi_ply_checked_count >= 3
    assert result.evidence["uses_capture_evaluation"] is True
    assert result.evidence["uses_opponent_reply_evaluation"] is True
    assert result.evidence["uses_multi_ply_lookahead"] is True


def test_phase22b15_finishes_winning_or_stable(tmp_path):
    result = run_full_chess_game_loop_kernel(memory_path=tmp_path / "game_loop_memory.json")

    assert result.material_gain_total > 0
    assert result.final_state_score > 0
    assert result.game_loop_winning_or_stable is True
    assert result.selected_opening_strategy == "STRAT-1 / LINE-1"
    assert len(result.game_loop_trace_hash) == 64


def test_phase22b15_persists_game_loop_memory(tmp_path):
    memory_path = tmp_path / "game_loop_memory.json"

    first = run_full_chess_game_loop_kernel(memory_path=memory_path)
    second = run_full_chess_game_loop_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_game_loop_policy["kernel_run_count"] >= 2
    assert second.final_game_loop_policy["game_loop_completion_count"] >= 2
    assert second.final_game_loop_policy["legal_turn_count"] >= 12
    assert second.final_game_loop_policy["king_safe_turn_count"] >= 12
    assert memory_path.exists()
