from pathlib import Path

from backend.modules.aion_games.full_chess_opponent_threat_map_kernel import (
    run_full_chess_opponent_threat_map_kernel,
)


def test_phase22e29_builds_threat_map(tmp_path: Path):
    result = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        aion_side="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.threat_map_active is True
    assert result.opponent_legal_move_count > 0
    assert result.top_threats


def test_phase22e29_detects_check_or_major_capture_threat(tmp_path: Path):
    result = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        aion_side="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.highest_threat_score >= 900
    assert result.recommended_response_mode in {
        "neutralise_critical_threat",
        "reduce_opponent_threats",
    }


def test_phase22e29_detects_promotion_threat(tmp_path: Path):
    result = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/6p1/4K3 w - - 0 1",
        aion_side="white",
        memory_path=tmp_path / "memory.json",
    )

    assert any(t["promotes"] for t in result.top_threats)
    assert result.high_threat_count >= 1


def test_phase22e29_continue_plan_when_no_major_threat(tmp_path: Path):
    result = run_full_chess_opponent_threat_map_kernel(
        input_fen="8/8/8/8/8/8/5k2/4K3 w - - 0 1",
        aion_side="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.recommended_response_mode in {
        "continue_plan",
        "reduce_opponent_threats",
        "neutralise_critical_threat",
    }
    assert result.highest_threat_score >= 0


def test_phase22e29_memory_persists(tmp_path: Path):
    memory_path = tmp_path / "memory.json"

    first = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        aion_side="white",
        memory_path=memory_path,
    )
    second = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        aion_side="white",
        memory_path=memory_path,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_threat_policy["kernel_run_count"] == 2


def test_phase22e29_boundary_no_engine_or_analysis(tmp_path: Path):
    result = run_full_chess_opponent_threat_map_kernel(
        input_fen="4k3/8/8/8/8/8/4q3/4KQ2 w - - 0 1",
        aion_side="white",
        memory_path=tmp_path / "memory.json",
    )

    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_llm_move_judgement"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert "opponent threat map" in result.boundary_statement
