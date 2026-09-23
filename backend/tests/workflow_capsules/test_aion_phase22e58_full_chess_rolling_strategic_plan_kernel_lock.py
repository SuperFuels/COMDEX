import chess

from backend.modules.aion_games.full_chess_rolling_strategic_plan_kernel import (
    run_full_chess_rolling_strategic_plan_kernel,
)


def test_phase22e58_opening_generates_rolling_plan_with_legal_move(tmp_path):
    result = run_full_chess_rolling_strategic_plan_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=tmp_path / "plan_memory.json",
        task_name="phase22e58_opening_plan_test",
    )

    board = chess.Board(chess.STARTING_FEN)

    assert result.phase == "opening"
    assert result.primary_plan == "rapid_development"
    assert result.secondary_plan == "central_control"
    assert result.fallback_plan
    assert result.setup_sequence
    assert result.selected_plan_move in [m.uci() for m in board.legal_moves]
    assert result.evidence["rolling_plan_generated"] is True
    assert result.evidence["selected_plan_move_legal"] is True
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_llm_move_judgement"] is False


def test_phase22e58_middlegame_tracks_opponent_disruption_and_forcing_moves(tmp_path):
    fen = "r1bqk2r/ppp2ppp/2n1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 2 7"

    result = run_full_chess_rolling_strategic_plan_kernel(
        input_fen=fen,
        side_to_move="white",
        memory_path=tmp_path / "plan_memory.json",
        task_name="phase22e58_middlegame_plan_test",
    )

    assert result.phase in {"opening", "middlegame"}
    assert result.primary_plan
    assert result.target_weakness
    assert result.opponent_disruption_risk in {"low", "medium", "high"}
    assert result.candidate_plan_moves
    assert result.evidence["opponent_disruption_risk_monitored"] is True


def test_phase22e58_memory_mutates_and_trace_is_stable_per_result(tmp_path):
    memory = tmp_path / "plan_memory.json"

    first = run_full_chess_rolling_strategic_plan_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory,
        task_name="phase22e58_memory_test",
    )
    second = run_full_chess_rolling_strategic_plan_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        memory_path=memory,
        task_name="phase22e58_memory_test",
    )

    assert first.policy_memory_mutated is True
    assert second.memory_loaded is True
    assert second.final_policy["kernel_run_count"] == 2
    assert first.trace_hash == second.trace_hash
