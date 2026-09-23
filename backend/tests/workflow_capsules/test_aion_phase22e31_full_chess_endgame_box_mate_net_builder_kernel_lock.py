from pathlib import Path

from backend.modules.aion_games.full_chess_endgame_box_mate_net_builder_kernel import (
    run_full_chess_endgame_box_mate_net_builder_kernel,
)


def test_phase22e31_detects_queen_vs_king_endgame(tmp_path: Path):
    result = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.endgame_box_mate_net_active is True
    assert result.detected_endgame_type == "king_queen_vs_king"
    assert result.selected_move_is_legal is True
    assert result.candidate_count > 0


def test_phase22e31_scores_enemy_king_box_metrics(tmp_path: Path):
    result = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    top = result.top_candidates[0]
    assert "enemy_king_mobility_after" in top
    assert "enemy_king_edge_distance_after" in top
    assert "own_king_distance_after" in top
    assert top["box_score"] == result.selected_score


def test_phase22e31_penalises_repeated_move(tmp_path: Path):
    clean = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "clean.json",
    )

    repeated = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        repeated_moves=[clean.selected_move],
        memory_path=tmp_path / "repeated.json",
    )

    matching = [c for c in repeated.top_candidates if c["move"] == clean.selected_move]
    if matching:
        assert matching[0]["repeated_move_penalty_applied"] is True


def test_phase22e31_detects_rook_vs_king_endgame(tmp_path: Path):
    result = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/8/8/8/8/3R4/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.detected_endgame_type == "king_rook_vs_king"
    assert result.selected_move_is_legal is True


def test_phase22e31_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )
    second = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_mate_net_policy["kernel_run_count"] == 2


def test_phase22e31_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_endgame_box_mate_net_builder_kernel(
        input_fen="8/1k6/3Q4/8/8/8/8/6K1 w - - 0 1",
        side_to_move="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "mate-net builder" in result.boundary_statement
