from backend.modules.aion_games import run_full_chess_multi_ply_lookahead_kernel


def test_phase22b14_evaluates_multi_ply_lines(tmp_path):
    result = run_full_chess_multi_ply_lookahead_kernel(memory_path=tmp_path / "multi_ply_memory.json")

    assert result.kernel_version == "phase22b14_full_chess_multi_ply_lookahead_kernel_v1"
    assert result.board_size == 8
    assert result.lookahead_depth >= 3
    assert result.candidate_line_count >= 5
    assert result.surviving_line_count >= 2
    assert result.evidence["uses_multi_ply_depth"] is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b14_rejects_greedy_king_and_material_loss_lines(tmp_path):
    result = run_full_chess_multi_ply_lookahead_kernel(memory_path=tmp_path / "multi_ply_memory.json")

    assert result.greedy_trap_rejection_count >= 1
    assert result.king_safety_rejection_count >= 1
    assert result.material_loss_rejection_count >= 1
    assert result.avoided_greedy_trap is True
    assert result.avoided_king_safety_failure is True
    assert result.avoided_material_loss_line is True


def test_phase22b14_selects_best_surviving_line(tmp_path):
    result = run_full_chess_multi_ply_lookahead_kernel(memory_path=tmp_path / "multi_ply_memory.json")

    assert result.selected_line["line_id"] == "LINE-1"
    assert result.selected_line_survives_depth is True
    assert result.selected_line_score > 0
    assert len(result.multi_ply_trace_hash) == 64
    assert result.evidence["selects_best_surviving_line"] is True


def test_phase22b14_persists_multi_ply_memory(tmp_path):
    memory_path = tmp_path / "multi_ply_memory.json"

    first = run_full_chess_multi_ply_lookahead_kernel(memory_path=memory_path)
    second = run_full_chess_multi_ply_lookahead_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_multi_ply_policy["kernel_run_count"] >= 2
    assert second.final_multi_ply_policy["multi_ply_selection_count"] >= 2
    assert second.final_multi_ply_policy["greedy_trap_rejection_count"] >= 2
    assert second.final_multi_ply_policy["king_safety_rejection_count"] >= 2
    assert second.final_multi_ply_policy["material_loss_rejection_count"] >= 2
    assert memory_path.exists()
