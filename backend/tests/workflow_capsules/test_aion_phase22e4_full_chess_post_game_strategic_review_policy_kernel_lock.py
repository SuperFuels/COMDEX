from pathlib import Path

import chess

from backend.modules.aion_games.full_chess_post_game_strategic_review_policy_kernel import (
    run_full_chess_post_game_strategic_review_policy_kernel,
)


def test_phase22e4_reviews_post_game_and_updates_policy(tmp_path: Path):
    result = run_full_chess_post_game_strategic_review_policy_kernel(
        memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.review_mode == "post_game_strategic_review_and_policy_update"
    assert result.evidence["post_game_strategic_review_active"] is True
    assert result.evidence["policy_update_active"] is True
    assert result.policy_update_count > 0
    assert result.review_trace_hash


def test_phase22e4_detects_mate_loss_and_king_policy(tmp_path: Path):
    result = run_full_chess_post_game_strategic_review_policy_kernel(
        memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        final_status="mate",
        winner="black",
        aion_colour="white",
    )

    assert "mate_loss" in result.strategic_failure_modes
    assert result.policy_updates["increase_king_safety_goal_bias_after_mate_loss"] is True


def test_phase22e4_detects_positional_decline(tmp_path: Path):
    result = run_full_chess_post_game_strategic_review_policy_kernel(
        memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        initial_fen=chess.STARTING_FEN,
        final_fen="4k3/8/8/8/8/8/6q1/4K3 w - - 0 1",
    )

    assert result.positional_delta < 0
    assert "positional_decline" in result.strategic_failure_modes
    assert result.policy_updates["increase_positional_delta_weight_after_decline"] is True


def test_phase22e4_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "review_memory.json"

    first = run_full_chess_post_game_strategic_review_policy_kernel(
        memory_path=memory_path,
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )
    second = run_full_chess_post_game_strategic_review_policy_kernel(
        memory_path=memory_path,
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_review_policy["kernel_run_count"] == 2
    assert second.final_review_policy["strategic_review_count"] == 2


def test_phase22e4_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_post_game_strategic_review_policy_kernel(
        memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
