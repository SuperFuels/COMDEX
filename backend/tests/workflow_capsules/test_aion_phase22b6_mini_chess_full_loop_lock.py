from backend.modules.aion_games import run_mini_chess_full_loop_lock


def test_phase22b6_full_loop_passes_all_mini_chess_locks(tmp_path):
    result = run_mini_chess_full_loop_lock(memory_path=tmp_path / "full_loop_memory.json")

    assert result.kernel_version == "phase22b6_mini_chess_full_loop_lock_v1"
    assert result.legal_move_lock_passed is True
    assert result.threat_map_lock_passed is True
    assert result.capture_material_lock_passed is True
    assert result.self_play_lock_passed is True
    assert result.opponent_win_lock_passed is True
    assert result.full_loop_passed is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b6_combined_summary_contains_each_phase(tmp_path):
    result = run_mini_chess_full_loop_lock(memory_path=tmp_path / "full_loop_memory.json")

    assert result.combined_summary["phase22b1_legal_move"]["passed"] is True
    assert result.combined_summary["phase22b2_threat_map"]["passed"] is True
    assert result.combined_summary["phase22b3_capture_material"]["passed"] is True
    assert result.combined_summary["phase22b4_self_play"]["passed"] is True
    assert result.combined_summary["phase22b5_opponent_win"]["passed"] is True
    assert len(result.combined_trace_hash) == 64


def test_phase22b6_persists_full_loop_memory(tmp_path):
    memory_path = tmp_path / "full_loop_memory.json"

    first = run_mini_chess_full_loop_lock(memory_path=memory_path)
    second = run_mini_chess_full_loop_lock(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_full_loop_policy["kernel_run_count"] >= 2
    assert second.final_full_loop_policy["full_loop_pass_count"] >= 2
    assert second.final_full_loop_policy["opponent_win_pass_count"] >= 2
    assert memory_path.exists()
