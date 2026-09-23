from backend.modules.aion_games import run_full_chess_one_ply_strategy_kernel


def test_phase22b13_combines_strategy_inputs(tmp_path):
    result = run_full_chess_one_ply_strategy_kernel(memory_path=tmp_path / "strategy_memory.json")

    assert result.kernel_version == "phase22b13_full_chess_one_ply_strategy_kernel_v1"
    assert result.board_size == 8
    assert result.candidate_strategy_count >= 6
    assert result.generated_legal_count >= 5
    assert result.safety_preserving_count >= 4
    assert result.safe_profitable_capture_count >= 1
    assert result.survives_opponent_reply_count >= 2
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b13_rejects_unsafe_bad_reply_and_bad_capture(tmp_path):
    result = run_full_chess_one_ply_strategy_kernel(memory_path=tmp_path / "strategy_memory.json")

    assert result.rejected_by_safety_count >= 1
    assert result.rejected_by_bad_reply_count >= 1
    assert result.rejected_by_bad_capture_count >= 1
    assert result.evidence["rejects_unsafe_strategy"] is True
    assert result.evidence["rejects_bad_reply_strategy"] is True
    assert result.evidence["rejects_bad_capture_strategy"] is True


def test_phase22b13_selects_best_one_ply_strategy(tmp_path):
    result = run_full_chess_one_ply_strategy_kernel(memory_path=tmp_path / "strategy_memory.json")

    assert result.selected_strategy["move_id"] == "STRAT-1"
    assert result.selected_strategy_is_legal is True
    assert result.selected_strategy_preserves_king is True
    assert result.selected_strategy_survives_reply is True
    assert result.selected_strategy_is_profitable is True
    assert result.selected_strategy_score > 0
    assert len(result.one_ply_strategy_trace_hash) == 64


def test_phase22b13_persists_strategy_memory(tmp_path):
    memory_path = tmp_path / "strategy_memory.json"

    first = run_full_chess_one_ply_strategy_kernel(memory_path=memory_path)
    second = run_full_chess_one_ply_strategy_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_strategy_policy["kernel_run_count"] >= 2
    assert second.final_strategy_policy["strategy_selection_count"] >= 2
    assert second.final_strategy_policy["safety_rejection_count"] >= 2
    assert second.final_strategy_policy["bad_reply_rejection_count"] >= 2
    assert memory_path.exists()
