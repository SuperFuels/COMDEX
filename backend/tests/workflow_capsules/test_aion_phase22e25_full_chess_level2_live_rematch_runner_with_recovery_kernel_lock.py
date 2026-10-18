from pathlib import Path

from backend.modules.aion_games.full_chess_level2_live_rematch_runner_with_recovery_kernel import (
    run_full_chess_level2_live_rematch_runner_with_recovery_kernel,
)

FEN_BEFORE = "rnb1kb1r/pp4p1/2pqp3/7p/2PP2n1/8/PP2BPPP/R1BQ1RK1 w kq - 2 13"
MOVES_BEFORE = [
    "g1f3", "c7c6", "b1c3", "d7d5", "f3g5", "f7f6",
    "e2e4", "g8h6", "g5f3", "d8d6", "d2d4", "e7e6",
]


def _failed_400_sender_record():
    return {
        "queen_endgame_override_active": False,
        "base_sender_consumed": True,
        "base_selected_move": "e2g4",
        "override_selected_move": "",
        "final_selected_move": "e2g4",
        "final_selected_move_is_legal": True,
        "move_post_attempted": True,
        "move_post_succeeded": False,
        "move_post_status_code": 400,
        "move_post_error": "HTTP Error 400: Bad Request",
    }


def test_phase22e25_continues_after_nonfatal_400_recovery(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="irUsTEpO",
        full_id="irUsTEpOFPu1",
        aion_colour="white",
        target_level=2,
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        sender_record=_failed_400_sender_record(),
        latest_state_after_failure={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=tmp_path / "memory.json",
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )

    assert result.recovery_invoked is True
    assert result.recovered_as_nonfatal is True
    assert result.continue_live_loop is True
    assert result.abort_live_loop is False
    assert result.count_move_as_successful is True
    assert result.next_loop_ply_count == len(MOVES_BEFORE) + 1


def test_phase22e25_normal_success_continues_without_recovery(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="ok",
        full_id="okFULL",
        aion_colour="white",
        target_level=2,
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        expected_moves_before=[],
        sender_record={
            "queen_endgame_override_active": False,
            "final_selected_move": "g1f3",
            "final_selected_move_is_legal": True,
            "move_post_attempted": True,
            "move_post_succeeded": True,
            "move_post_status_code": 200,
        },
        memory_path=tmp_path / "memory.json",
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )

    assert result.recovery_invoked is False
    assert result.continue_live_loop is True
    assert result.next_loop_moves == ["g1f3"]


def test_phase22e25_hard_failure_aborts(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="irUsTEpO",
        full_id="irUsTEpOFPu1",
        aion_colour="white",
        target_level=2,
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        sender_record=_failed_400_sender_record(),
        latest_state_after_failure={"status": "started", "moves": " ".join(MOVES_BEFORE)},
        memory_path=tmp_path / "memory.json",
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )

    assert result.recovery_invoked is True
    assert result.recovered_as_nonfatal is False
    assert result.continue_live_loop is False
    assert result.abort_live_loop is True


def test_phase22e25_records_queen_override_when_seen(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="queen",
        full_id="queenFULL",
        aion_colour="white",
        target_level=2,
        fen_before="8/1k6/3Q4/8/r7/8/P4PPP/6KR w - - 11 61",
        expected_moves_before=[],
        sender_record={
            "queen_endgame_override_active": True,
            "final_selected_move": "d6c7",
            "final_selected_move_is_legal": True,
            "move_post_attempted": True,
            "move_post_succeeded": True,
            "move_post_status_code": 200,
        },
        memory_path=tmp_path / "memory.json",
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )

    assert result.queen_override_enabled is True
    assert result.queen_endgame_override_active is True
    assert result.continue_live_loop is True
    assert result.final_runner_policy["queen_override_seen_count"] == 1


def test_phase22e25_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="irUsTEpO",
        full_id="irUsTEpOFPu1",
        aion_colour="white",
        target_level=2,
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        sender_record=_failed_400_sender_record(),
        latest_state_after_failure={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=memory_path,
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )
    second = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="irUsTEpO",
        full_id="irUsTEpOFPu1",
        aion_colour="white",
        target_level=2,
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        sender_record=_failed_400_sender_record(),
        latest_state_after_failure={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=memory_path,
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_runner_policy["kernel_run_count"] == 2


def test_phase22e25_boundary_no_engine_analysis_or_live_send(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_runner_with_recovery_kernel(
        game_id="irUsTEpO",
        full_id="irUsTEpOFPu1",
        aion_colour="white",
        target_level=2,
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        sender_record=_failed_400_sender_record(),
        latest_state_after_failure={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=tmp_path / "memory.json",
        recovery_loop_memory_path=tmp_path / "recovery_loop_memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not send moves" in result.boundary_statement
