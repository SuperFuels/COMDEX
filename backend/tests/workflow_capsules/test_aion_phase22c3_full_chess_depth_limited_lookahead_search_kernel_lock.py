import chess

from backend.modules.aion_games import run_full_chess_depth_limited_lookahead_search_kernel


def test_phase22c3_searches_from_start_position(tmp_path):
    result = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )

    board = chess.Board()
    legal = {move.uci() for move in board.legal_moves}

    assert result.kernel_version == "phase22c3_full_chess_depth_limited_lookahead_search_kernel_v1"
    assert result.search_mode == "depth_limited_lookahead_search"
    assert result.selected_move in legal
    assert result.legal_move_count == 20
    assert result.candidate_count == 20
    assert result.searched_node_count > 0


def test_phase22c3_simulates_opponent_replies(tmp_path):
    result = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )

    assert result.evidence["opponent_replies_simulated"] is True
    assert result.leaf_evaluation_count > 0
    assert len(result.top_candidate_lines) > 0


def test_phase22c3_prioritises_mate_in_one(tmp_path):
    board = chess.Board("6k1/5Q2/6K1/8/8/8/8/8 w - - 0 1")

    result = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        fen=board.fen(),
        depth_limit=2,
    )

    candidate_mates = [
        item for item in result.top_candidate_lines
        if item["is_checkmate"] is True
    ]

    assert result.selected_reason == "depth_search_terminal_mate"
    assert result.top_candidate_lines[0]["is_checkmate"] is True
    assert result.selected_move == result.top_candidate_lines[0]["move"]
    assert candidate_mates


def test_phase22c3_respects_terminal_position_no_move(tmp_path):
    board = chess.Board()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        board.push_uci(move)

    result = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        fen=board.fen(),
        depth_limit=2,
    )

    assert result.terminal_position is True
    assert result.no_legal_moves is True
    assert result.selected_move == ""
    assert result.selected_reason == "no_legal_move_available"
    assert result.evidence["no_illegal_move_emitted"] is True


def test_phase22c3_is_deterministic(tmp_path):
    result_one = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory_one.json",
        evaluation_memory_path=tmp_path / "evaluation_memory_one.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )
    result_two = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory_two.json",
        evaluation_memory_path=tmp_path / "evaluation_memory_two.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )

    assert result_one.selected_move == result_two.selected_move
    assert result_one.selected_score == result_two.selected_score
    assert result_one.search_trace_hash == result_two.search_trace_hash


def test_phase22c3_persists_memory(tmp_path):
    memory_path = tmp_path / "search_memory.json"

    first = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=memory_path,
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )
    second = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=memory_path,
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_search_policy["kernel_run_count"] >= 2
    assert second.final_search_policy["search_count"] >= 2
    assert memory_path.exists()


def test_phase22c3_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_depth_limited_lookahead_search_kernel(
        memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        depth_limit=2,
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert len(result.search_trace_hash) == 64
