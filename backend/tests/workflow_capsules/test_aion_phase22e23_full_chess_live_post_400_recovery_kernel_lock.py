from pathlib import Path

from backend.modules.aion_games.full_chess_live_post_400_recovery_kernel import (
    run_full_chess_live_post_400_recovery_kernel,
)

FEN_BEFORE = "rnb1kb1r/pp4p1/2pqp3/7p/2PP2n1/8/PP2BPPP/R1BQ1RK1 w kq - 2 13"
MOVES_BEFORE = [
    "g1f3", "c7c6", "b1c3", "d7d5", "f3g5", "f7f6",
    "e2e4", "g8h6", "g5f3", "d8d6", "d2d4", "e7e6",
]


def test_phase22e23_recovers_when_move_already_present(tmp_path: Path):
    result = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        move_post_error="HTTP Error 400: Bad Request",
        latest_state={
            "status": "started",
            "moves": " ".join(MOVES_BEFORE + ["e2g4"]),
        },
        memory_path=tmp_path / "memory.json",
    )

    assert result.recovery_triggered is True
    assert result.latest_state_fetch_succeeded is True
    assert result.attempted_move_already_present is True
    assert result.recovered_as_nonfatal is True
    assert result.abort_recommended is False


def test_phase22e23_recovers_stale_state_when_server_advanced(tmp_path: Path):
    result = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        latest_state={
            "status": "started",
            "moves": " ".join(MOVES_BEFORE + ["a7a6"]),
        },
        memory_path=tmp_path / "memory.json",
    )

    assert result.server_ply_advanced is True
    assert result.stale_state_detected is True
    assert result.recovered_as_nonfatal is True
    assert result.abort_recommended is False


def test_phase22e23_aborts_when_current_state_rejects_move(tmp_path: Path):
    result = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        latest_state={
            "status": "started",
            "moves": " ".join(MOVES_BEFORE),
        },
        memory_path=tmp_path / "memory.json",
    )

    assert result.latest_state_fetch_succeeded is True
    assert result.server_ply_advanced is False
    assert result.abort_recommended is True
    assert result.failure_classification == "post_400_confirmed_current_state_rejected_move"


def test_phase22e23_non_400_remains_hard_failure(tmp_path: Path):
    result = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=401,
        latest_state={},
        memory_path=tmp_path / "memory.json",
    )

    assert result.recovery_triggered is False
    assert result.abort_recommended is True
    assert result.failure_classification == "non_400_post_failure"


def test_phase22e23_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=memory_path,
    )
    second = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_recovery_policy["kernel_run_count"] == 2


def test_phase22e23_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_live_post_400_recovery_kernel(
        game_id="irUsTEpO",
        attempted_move="e2g4",
        fen_before=FEN_BEFORE,
        expected_moves_before=MOVES_BEFORE,
        move_post_succeeded_initially=False,
        move_post_status_code=400,
        latest_state={"status": "started", "moves": " ".join(MOVES_BEFORE + ["e2g4"])},
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "does not use Lichess analysis" in result.boundary_statement
