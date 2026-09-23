import chess

from backend.modules.aion_games import run_full_chess_evaluation_guided_move_selection_kernel


def test_phase22c2_selects_legal_move_from_start(tmp_path):
    result = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    board = chess.Board()
    legal = {move.uci() for move in board.legal_moves}

    assert result.kernel_version == "phase22c2_full_chess_evaluation_guided_move_selection_kernel_v1"
    assert result.selection_mode == "evaluation_guided_move_selection"
    assert result.selected_move in legal
    assert result.legal_move_count == 20
    assert result.candidate_count == 20


def test_phase22c2_scores_candidates(tmp_path):
    result = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert len(result.top_candidate_moves) > 0
    assert "move" in result.top_candidate_moves[0]
    assert "score_after" in result.top_candidate_moves[0]
    assert result.evidence["candidate_moves_scored"] is True


def test_phase22c2_selects_a_highest_scored_move_deterministically(tmp_path):
    result_one = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory_one.json",
        evaluation_memory_path=tmp_path / "evaluation_memory_one.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    result_two = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory_two.json",
        evaluation_memory_path=tmp_path / "evaluation_memory_two.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result_one.selected_move == result_two.selected_move
    assert result_one.selected_score == result_two.selected_score
    assert result_one.selection_trace_hash == result_two.selection_trace_hash


def test_phase22c2_respects_terminal_position_no_move(tmp_path):
    board = chess.Board()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        board.push_uci(move)

    result = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        fen=board.fen(),
    )

    assert result.terminal_position is True
    assert result.no_legal_moves is True
    assert result.selected_move == ""
    assert result.selected_reason == "no_legal_move_available"
    assert result.evidence["no_illegal_move_emitted"] is True


def test_phase22c2_persists_memory(tmp_path):
    memory_path = tmp_path / "selection_memory.json"

    first = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=memory_path,
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=memory_path,
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_selection_policy["kernel_run_count"] >= 2
    assert second.final_selection_policy["selection_count"] >= 2
    assert memory_path.exists()


def test_phase22c2_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_evaluation_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert len(result.selection_trace_hash) == 64
