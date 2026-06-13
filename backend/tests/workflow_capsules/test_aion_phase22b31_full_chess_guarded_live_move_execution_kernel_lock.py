from backend.modules.aion_games import run_full_chess_guarded_live_move_execution_kernel


def test_phase22b31_builds_guarded_dry_run_request(tmp_path):
    result = run_full_chess_guarded_live_move_execution_kernel(
        memory_path=tmp_path / "guarded_live_move_memory.json"
    )

    assert result.kernel_version == "phase22b31_full_chess_guarded_live_move_execution_kernel_v1"
    assert result.execution_mode == "guarded_dry_run_live_move_execution"
    assert result.request["dry_run"] is True
    assert result.request["allow_network"] is False
    assert result.network_call_performed is False
    assert result.live_write_blocked is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b31_validates_move_endpoint_and_method(tmp_path):
    result = run_full_chess_guarded_live_move_execution_kernel(
        memory_path=tmp_path / "guarded_live_move_memory.json"
    )

    assert result.guard_decision["valid_move_shape"] is True
    assert result.guard_decision["valid_endpoint"] is True
    assert result.guard_decision["valid_method"] is True
    assert result.selected_bestmove == "c4d5"
    assert result.game_id == "aion-demo-game-001"
    assert result.would_post_move is True


def test_phase22b31_blocks_live_write_by_default(tmp_path):
    result = run_full_chess_guarded_live_move_execution_kernel(
        memory_path=tmp_path / "guarded_live_move_memory.json"
    )

    assert result.guard_decision["execution_allowed"] is False
    assert result.guard_decision["block_reason"] == "dry_run_guard_active"
    assert result.dry_run_preview_emitted is True
    assert result.live_write_blocked is True
    assert result.evidence["execution_not_allowed_without_all_guards"] is True
    assert result.evidence["emits_dry_run_preview"] is True


def test_phase22b31_emits_trace_hash(tmp_path):
    result = run_full_chess_guarded_live_move_execution_kernel(
        memory_path=tmp_path / "guarded_live_move_memory.json"
    )

    assert len(result.guarded_execution_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b31_persists_guarded_execution_memory(tmp_path):
    memory_path = tmp_path / "guarded_live_move_memory.json"

    first = run_full_chess_guarded_live_move_execution_kernel(memory_path=memory_path)
    second = run_full_chess_guarded_live_move_execution_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_guarded_execution_policy["kernel_run_count"] >= 2
    assert second.final_guarded_execution_policy["guarded_execution_session_count"] >= 2
    assert second.final_guarded_execution_policy["dry_run_preview_count"] >= 2
    assert second.final_guarded_execution_policy["blocked_live_write_count"] >= 2
    assert second.final_guarded_execution_policy["network_call_count"] == 0
    assert memory_path.exists()
