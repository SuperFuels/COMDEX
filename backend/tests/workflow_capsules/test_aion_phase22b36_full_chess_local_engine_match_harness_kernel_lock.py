from backend.modules.aion_games import run_full_chess_local_engine_match_harness_kernel


def test_phase22b36_runs_local_match_harness(tmp_path):
    result = run_full_chess_local_engine_match_harness_kernel(
        memory_path=tmp_path / "local_match_memory.json"
    )

    assert result.kernel_version == "phase22b36_full_chess_local_engine_match_harness_kernel_v1"
    assert result.harness_mode == "local_offline_match_harness"
    assert result.network_call_performed is False
    assert result.human_approval_required is False
    assert result.opponent_profile_count == 5
    assert result.match_count == 5
    assert result.completed_match_count == 5
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b36_covers_required_opponents(tmp_path):
    result = run_full_chess_local_engine_match_harness_kernel(
        memory_path=tmp_path / "local_match_memory.json"
    )

    assert result.evidence["runs_random_bot_match"] is True
    assert result.evidence["runs_greedy_bot_match"] is True
    assert result.evidence["runs_tactical_bot_match"] is True
    assert result.evidence["runs_self_play_match"] is True
    assert result.evidence["runs_simple_rated_tier_match"] is True


def test_phase22b36_records_score_and_threshold(tmp_path):
    result = run_full_chess_local_engine_match_harness_kernel(
        memory_path=tmp_path / "local_match_memory.json"
    )

    assert result.win_count == 2
    assert result.draw_count == 2
    assert result.loss_count == 1
    assert result.score_total == 3.0
    assert result.score_percentage == 60.0
    assert result.local_match_passed is True
    assert result.evidence["passes_local_match_threshold"] is True


def test_phase22b36_emits_trace_hash(tmp_path):
    result = run_full_chess_local_engine_match_harness_kernel(
        memory_path=tmp_path / "local_match_memory.json"
    )

    assert len(result.local_match_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b36_persists_local_match_memory(tmp_path):
    memory_path = tmp_path / "local_match_memory.json"

    first = run_full_chess_local_engine_match_harness_kernel(memory_path=memory_path)
    second = run_full_chess_local_engine_match_harness_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_local_match_policy["kernel_run_count"] >= 2
    assert second.final_local_match_policy["local_match_session_count"] >= 2
    assert second.final_local_match_policy["local_match_total"] >= 10
    assert memory_path.exists()
