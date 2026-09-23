import chess

from backend.modules.aion_games import run_full_chess_real_evaluation_function_kernel


def test_phase22c1_evaluates_starting_position(tmp_path):
    result = run_full_chess_real_evaluation_function_kernel(
        memory_path=tmp_path / "memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.kernel_version == "phase22c1_full_chess_real_evaluation_function_kernel_v1"
    assert result.evaluation_mode == "real_chess_position_evaluation"
    assert result.fen == chess.STARTING_FEN
    assert result.side_to_evaluate == "white"
    assert result.legal_move_count == 20
    assert result.material_score == 0
    assert result.evidence["evaluation_function_active"] is True


def test_phase22c1_scores_material_advantage(tmp_path):
    fen = "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    result = run_full_chess_real_evaluation_function_kernel(
        memory_path=tmp_path / "memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        fen=fen,
        side_to_evaluate="white",
    )

    assert result.material_score >= 800
    assert result.total_score > 0


def test_phase22c1_detects_terminal_checkmate(tmp_path):
    board = chess.Board()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        board.push_uci(move)

    result = run_full_chess_real_evaluation_function_kernel(
        memory_path=tmp_path / "memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        fen=board.fen(),
        side_to_evaluate="white",
    )

    assert result.is_checkmate is True
    assert result.terminal_score == -100000
    assert result.total_score < -90000


def test_phase22c1_scores_candidate_moves(tmp_path):
    result = run_full_chess_real_evaluation_function_kernel(
        memory_path=tmp_path / "memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.best_scored_move
    assert len(result.top_candidate_moves) > 0
    assert "weighted_score" in result.top_candidate_moves[0]
    assert result.evidence["candidate_moves_scored"] is True


def test_phase22c1_loads_post_game_learning_weights(tmp_path):
    post_game_memory = tmp_path / "post_game.json"
    post_game_memory.write_text(
        """
{
  "post_game_blunder_review_policy": {
    "strategy_weight_king_safety": 1.2,
    "strategy_weight_piece_activity": 1.1,
    "strategy_weight_repetition_penalty": 1.3,
    "strategy_weight_queen_activity_penalty": 1.0
  }
}
""",
        encoding="utf-8",
    )

    result = run_full_chess_real_evaluation_function_kernel(
        memory_path=tmp_path / "memory.json",
        post_game_memory_path=post_game_memory,
    )

    assert result.learned_policy_weights["strategy_weight_king_safety"] == 1.2
    assert result.learned_policy_weights["strategy_weight_repetition_penalty"] == 1.3
    assert result.evidence["post_game_learning_loaded"] is True


def test_phase22c1_persists_memory(tmp_path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_real_evaluation_function_kernel(
        memory_path=memory_path,
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_real_evaluation_function_kernel(
        memory_path=memory_path,
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_evaluation_policy["kernel_run_count"] >= 2
    assert second.final_evaluation_policy["evaluation_count"] >= 2
    assert memory_path.exists()


def test_phase22c1_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_real_evaluation_function_kernel(
        memory_path=tmp_path / "memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert len(result.evaluation_trace_hash) == 64
