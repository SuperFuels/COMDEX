from backend.modules.aion_games import run_full_chess_post_game_blunder_review_kernel


def test_phase22b42_reviews_completed_live_game(tmp_path):
    result = run_full_chess_post_game_blunder_review_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.kernel_version == "phase22b42_full_chess_post_game_blunder_review_kernel_v1"
    assert result.review_mode == "post_game_blunder_review"
    assert result.game_id == "cPv6iyKb"
    assert result.opponent == "Stockfish level 1"
    assert result.final_status == "mate"
    assert result.winner == "white"
    assert result.aion_result == "win"


def test_phase22b42_analyzes_moves_and_aion_moves(tmp_path):
    result = run_full_chess_post_game_blunder_review_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.analyzed_ply_count == 61
    assert result.analyzed_aion_move_count == 31
    assert len(result.move_reviews) == 61


def test_phase22b42_detects_learning_signals(tmp_path):
    result = run_full_chess_post_game_blunder_review_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.repeated_cycle_detected is True
    assert result.repeated_cycle_count >= 1
    assert result.suboptimal_pattern_count >= result.repeated_cycle_count
    assert result.strongest_positive_signal == "terminal_mate_win"
    assert result.strongest_negative_signal == "repetitive_piece_shuffling"


def test_phase22b42_mutates_policy_memory(tmp_path):
    result = run_full_chess_post_game_blunder_review_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert result.policy_memory_mutated is True
    assert result.applied_policy_updates["strategy_weight_repetition_penalty"] > 0
    assert result.final_post_game_learning_policy["strategy_weight_repetition_penalty"] > 1.0


def test_phase22b42_learning_summary_is_emitted(tmp_path):
    result = run_full_chess_post_game_blunder_review_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert any("completed a live game" in item for item in result.learning_summary)
    assert any("repeated piece movement" in item for item in result.learning_summary)
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b42_emits_trace_hash(tmp_path):
    result = run_full_chess_post_game_blunder_review_kernel(
        memory_path=tmp_path / "memory.json"
    )

    assert len(result.post_game_review_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b42_persists_memory(tmp_path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_post_game_blunder_review_kernel(memory_path=memory_path)
    second = run_full_chess_post_game_blunder_review_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_post_game_learning_policy["kernel_run_count"] >= 2
    assert second.final_post_game_learning_policy["post_game_review_count"] >= 2
    assert memory_path.exists()
