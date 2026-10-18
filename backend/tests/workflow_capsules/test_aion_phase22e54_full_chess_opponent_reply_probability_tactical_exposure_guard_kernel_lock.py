from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_opponent_reply_probability_tactical_exposure_guard_kernel import (
    run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel,
)


LEVEL8_FAILURE_FEN = "r1b1k2r/p4ppp/2p1p3/2P5/2Pq4/5P2/Pb4PP/R3K2R w KQkq - 0 15"


def test_phase22e54_blocks_h2h4_in_center_control_under_tactical_exposure(tmp_path):
    result = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        selected_move="h2h4",
        active_intent="center_control",
        memory_path=tmp_path / "memory.json",
    )

    assert result.opponent_reply_probability_used is True
    assert result.one_ply_search_used is True
    assert result.two_ply_search_used is True
    assert result.value_function_used is True
    assert result.candidate_beam_search_used is True
    assert result.blunder_filter_used is True
    assert result.wing_pawn_lunge_detected is True
    assert result.center_control_h2h4_blocked is True
    assert result.final_selected_move != "h2h4"
    assert result.final_selected_move_is_legal is True


def test_phase22e54_scores_opponent_replies_without_stockfish_llm_or_lichess(tmp_path):
    result = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        selected_move="h2h4",
        active_intent="center_control",
        memory_path=tmp_path / "memory.json",
    )

    assert result.tactical_motifs_used is True
    assert result.policy_prior_used is True
    assert result.self_play_memory_used is True
    assert result.position_memory_used is True
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.trace_hash


def test_phase22e54_candidate_scores_are_legal_and_have_reply_probabilities(tmp_path):
    result = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        selected_move="h2h4",
        active_intent="center_control",
        memory_path=tmp_path / "memory.json",
    )

    board = chess.Board(LEVEL8_FAILURE_FEN)
    assert len(result.candidate_scores) >= 2
    assert any(item["reply_probability_total"] >= 0 for item in result.candidate_scores)
    assert chess.Move.from_uci(result.final_selected_move) in board.legal_moves


def test_phase22e54_memory_persists_policy_counts(tmp_path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        selected_move="h2h4",
        active_intent="center_control",
        memory_path=memory_path,
    )
    second = run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel(
        input_fen=LEVEL8_FAILURE_FEN,
        side_to_move="white",
        selected_move="h2h4",
        active_intent="center_control",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert memory_path.exists()
