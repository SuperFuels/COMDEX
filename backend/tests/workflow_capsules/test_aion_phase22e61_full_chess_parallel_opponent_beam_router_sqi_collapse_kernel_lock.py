import chess

from backend.modules.aion_games.full_chess_parallel_opponent_beam_router_sqi_collapse_kernel import (
    run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel,
)


def test_phase22e61_routes_multiple_candidates_through_parallel_opponent_beams(tmp_path):
    result = run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_moves=["g1f3", "b1c3", "e2e4", "d2d4"],
        primary_plan="rapid_development",
        target_weakness="undeveloped_position",
        max_candidates=4,
        max_reply_beams=8,
        max_continuations_per_reply=16,
        max_parallel_beams=1000,
        memory_path=tmp_path / "phase22e61_memory.json",
        task_name="phase22e61_parallel_router_test",
    )

    assert result.evidence["phase22e61_parallel_opponent_beam_router_used"] is True
    assert result.evidence["phase22e60_opponent_response_beam_planner_consumed"] is True
    assert result.candidate_count == 4
    assert result.generated_parallel_beam_count > 4
    assert result.evidence["can_scale_to_1000_beam_budget"] is True
    assert result.selected_move in {"g1f3", "b1c3", "e2e4", "d2d4"}
    assert result.sqi_collapse_packet["packet_type"] == "aion_chess_parallel_opponent_beam_sqi_collapse"
    assert result.qqc_router_packet["packet_type"] == "aion_chess_parallel_opponent_beam_qqc_router"
    assert result.hexcore_router_packet["packet_type"] == "aion_chess_parallel_opponent_beam_hexcore_router"
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["does_not_post_moves"] is True


def test_phase22e61_rejects_high_risk_candidate_when_mate_beam_exists(tmp_path):
    fen_after_f3_e5 = "rnbqkbnr/pppp1ppp/8/4p3/8/5P2/PPPPP1PP/RNBQKBNR w KQkq - 0 2"

    result = run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
        input_fen=fen_after_f3_e5,
        side_to_move="white",
        candidate_moves=["g2g4", "e2e4", "g1h3"],
        primary_plan="king_safety",
        target_weakness="king_safety",
        max_candidates=3,
        max_reply_beams=8,
        max_continuations_per_reply=12,
        max_parallel_beams=1000,
        collapse_threshold=0.62,
        memory_path=tmp_path / "phase22e61_memory.json",
        task_name="phase22e61_reject_mate_beam_test",
    )

    rows = {item["candidate_move"]: item for item in result.candidate_results}
    assert "g2g4" in rows
    assert rows["g2g4"]["top_reply_move"] == "d8h4"
    assert rows["g2g4"]["top_beam_mode"] in {"mate", "check"}
    assert rows["g2g4"]["accepted_by_collapse"] is False
    assert "g2g4" in result.rejected_moves
    assert result.selected_move != "g2g4"


def test_phase22e61_memory_mutates_and_trace_is_stable(tmp_path):
    memory = tmp_path / "phase22e61_memory.json"

    first = run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_moves=["g1f3", "b1c3"],
        max_candidates=2,
        max_reply_beams=6,
        max_continuations_per_reply=8,
        memory_path=memory,
        task_name="phase22e61_memory_test",
    )
    second = run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_moves=["g1f3", "b1c3"],
        max_candidates=2,
        max_reply_beams=6,
        max_continuations_per_reply=8,
        memory_path=memory,
        task_name="phase22e61_memory_test",
    )

    assert first.policy_memory_mutated is True
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2
    assert first.trace_hash == second.trace_hash
