from pathlib import Path

from backend.modules.aion_games.full_chess_self_play_curriculum_kernel import (
    run_full_chess_self_play_curriculum_kernel,
)


def test_phase22e5_runs_curriculum_with_increasing_difficulty(tmp_path: Path):
    result = run_full_chess_self_play_curriculum_kernel(
        memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
        episode_count=4,
    )

    assert result.curriculum_mode == "self_play_curriculum_with_increasing_difficulty"
    assert result.completed_episode_count == 4
    assert result.difficulty_increased is True
    assert result.final_curriculum_level > result.initial_curriculum_level
    assert result.evidence["self_play_curriculum_active"] is True
    assert result.evidence["post_game_policy_updates_consumed"] is True


def test_phase22e5_tracks_curriculum_metrics(tmp_path: Path):
    result = run_full_chess_self_play_curriculum_kernel(
        memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.plan_follow_rate > 0
    assert result.mate_loss_reduction_rate == 1.0
    assert result.promotion_danger_reduction_rate == 1.0
    assert result.invasion_risk_reduction_rate == 1.0
    assert result.average_episode_score > 0
    assert result.curriculum_trace_hash


def test_phase22e5_applies_policy_profile_from_review(tmp_path: Path):
    result = run_full_chess_self_play_curriculum_kernel(
        memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.selected_policy_profile == "CURRICULUM-KING-SAFETY"
    assert result.final_curriculum_policy["curriculum_weights"]["king_safety_pressure"] > 1.0
    assert result.final_curriculum_policy["curriculum_weights"]["invasion_reduction_pressure"] > 1.0
    assert result.final_curriculum_policy["curriculum_weights"]["positional_delta_pressure"] > 1.0


def test_phase22e5_memory_persists_across_runs(tmp_path: Path):
    memory_path = tmp_path / "curriculum_memory.json"

    first = run_full_chess_self_play_curriculum_kernel(
        memory_path=memory_path,
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )
    second = run_full_chess_self_play_curriculum_kernel(
        memory_path=memory_path,
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_curriculum_policy["kernel_run_count"] == 2
    assert second.final_curriculum_policy["curriculum_run_count"] == 2


def test_phase22e5_boundary_no_external_engines(tmp_path: Path):
    result = run_full_chess_self_play_curriculum_kernel(
        memory_path=tmp_path / "curriculum_memory.json",
        review_memory_path=tmp_path / "review_memory.json",
        plan_memory_path=tmp_path / "plan_memory.json",
        strategic_memory_path=tmp_path / "strategic_memory.json",
        feature_memory_path=tmp_path / "feature_memory.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["uses_trace_hash"] is True
