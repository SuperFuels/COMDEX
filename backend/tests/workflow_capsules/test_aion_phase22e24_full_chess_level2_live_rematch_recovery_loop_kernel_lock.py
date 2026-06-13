from pathlib import Path

from backend.modules.aion_games.full_chess_level2_live_rematch_recovery_loop_kernel import (
    run_full_chess_level2_live_rematch_recovery_loop_kernel,
)

FEN_BEFORE = "rnb1kb1r/pp4p1/2pqp3/7p/2PP2n1/8/PP2BPPP/R1BQ1RK1 w kq - 2 13"
MOVES_BEFORE = [
    "g1f3", "c7c6", "b1c3", "d7d5", "f3g5", "f7f6",
    "e2e4", "g8h6", "g5f3", "d8d6", "d2d4", "e7e6",
]


def test_phase22e24_continues_after_recovered_400_move_already_present(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=400,
        move_post_error="HTTP Error 400: Bad Request",
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=tmp_path / "memory.json",
        recovery_memory_path=tmp_path / "recovery_memory.json",
    )

    assert result.recovery_invoked is True
    assert result.recovered_as_nonfatal is True
    assert result.continue_live_loop is True
    assert result.abort_live_loop is False
    assert result.count_move_as_successful is True
    assert result.refresh_required is True


def test_phase22e24_continues_normal_success_without_recovery(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="ok",
        attempted_move="g1f3",
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        expected_moves_before=[],
        move_post_attempted=True,
        move_post_succeeded=True,
        move_post_status_code=200,
        memory_path=tmp_path / "memory.json",
    )

    assert result.recovery_invoked is False
    assert result.continue_live_loop is True
    assert result.abort_live_loop is False
    assert result.count_move_as_successful is True


def test_phase22e24_aborts_confirmed_current_state_rejection(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE)},
        memory_path=tmp_path / "memory.json",
        recovery_memory_path=tmp_path / "recovery_memory.json",
    )

    assert result.recovery_invoked is True
    assert result.recovered_as_nonfatal is False
    assert result.continue_live_loop is False
    assert result.abort_live_loop is True


def test_phase22e24_aborts_non_400_failure(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=401,
        memory_path=tmp_path / "memory.json",
    )

    assert result.recovery_invoked is False
    assert result.continue_live_loop is False
    assert result.abort_live_loop is True


def test_phase22e24_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=memory_path,
        recovery_memory_path=tmp_path / "recovery_memory.json",
    )
    second = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=memory_path,
        recovery_memory_path=tmp_path / "recovery_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_loop_policy["kernel_run_count"] == 2


def test_phase22e24_boundary_no_engine_analysis_or_send(tmp_path: Path):
    result = run_full_chess_level2_live_rematch_recovery_loop_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_attempted=True,
        move_post_succeeded=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=tmp_path / "memory.json",
        recovery_memory_path=tmp_path / "recovery_memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not send moves" in result.boundary_statement
