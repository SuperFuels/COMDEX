from backend.modules.aion_games import run_full_chess_local_tournament_rating_ladder_kernel


def test_phase22b37_runs_local_tournament_rating_ladder(tmp_path):
    result = run_full_chess_local_tournament_rating_ladder_kernel(
        memory_path=tmp_path / "ladder_memory.json"
    )

    assert result.kernel_version == "phase22b37_full_chess_local_tournament_rating_ladder_kernel_v1"
    assert result.ladder_mode == "local_offline_tournament_rating_ladder"
    assert result.network_call_performed is False
    assert result.human_approval_required is False
    assert result.tier_count == 5
    assert result.total_games_played == 10
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b37_covers_required_rating_tiers(tmp_path):
    result = run_full_chess_local_tournament_rating_ladder_kernel(
        memory_path=tmp_path / "ladder_memory.json"
    )

    assert result.evidence["runs_250_tier"] is True
    assert result.evidence["runs_500_tier"] is True
    assert result.evidence["runs_800_tier"] is True
    assert result.evidence["runs_1000_tier"] is True
    assert result.evidence["runs_1200_tier"] is True


def test_phase22b37_computes_ladder_rating_band(tmp_path):
    result = run_full_chess_local_tournament_rating_ladder_kernel(
        memory_path=tmp_path / "ladder_memory.json"
    )

    assert result.passed_tier_count == 3
    assert result.failed_tier_count == 2
    assert result.highest_passed_tier == 800
    assert result.lowest_failed_tier == 1000
    assert result.estimated_rating_floor == 800
    assert result.estimated_rating_ceiling == 1000
    assert result.estimated_rating_band_label == "early tactical ladder"
    assert result.ladder_passed is True


def test_phase22b37_emits_trace_hash(tmp_path):
    result = run_full_chess_local_tournament_rating_ladder_kernel(
        memory_path=tmp_path / "ladder_memory.json"
    )

    assert len(result.ladder_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b37_persists_ladder_memory(tmp_path):
    memory_path = tmp_path / "ladder_memory.json"

    first = run_full_chess_local_tournament_rating_ladder_kernel(memory_path=memory_path)
    second = run_full_chess_local_tournament_rating_ladder_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_ladder_policy["kernel_run_count"] >= 2
    assert second.final_ladder_policy["ladder_session_count"] >= 2
    assert second.final_ladder_policy["ladder_game_total"] >= 20
    assert memory_path.exists()
