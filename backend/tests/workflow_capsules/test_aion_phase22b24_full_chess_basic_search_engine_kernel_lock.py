from backend.modules.aion_games import run_full_chess_basic_search_engine_kernel


def test_phase22b24_runs_basic_search(tmp_path):
    result = run_full_chess_basic_search_engine_kernel(
        memory_path=tmp_path / "basic_search_memory.json"
    )

    assert result.kernel_version == "phase22b24_full_chess_basic_search_engine_kernel_v1"
    assert result.board_size == 8
    assert result.search_depth == 2
    assert result.candidate_move_count >= 5
    assert result.evaluated_node_count >= 10
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b24_scores_and_selects_best_move(tmp_path):
    result = run_full_chess_basic_search_engine_kernel(
        memory_path=tmp_path / "basic_search_memory.json"
    )

    assert result.selected_move_id == "SEARCH-1"
    assert result.selected_uci_move == "c4d5"
    assert result.selected_move_score > 0
    assert result.selected_move_preserves_king is True
    assert result.selected_move_profitable is True
    assert result.evidence["selects_best_accepted_move"] is True


def test_phase22b24_rejects_bad_lines(tmp_path):
    result = run_full_chess_basic_search_engine_kernel(
        memory_path=tmp_path / "basic_search_memory.json"
    )

    assert result.rejected_move_count >= 3
    assert result.bad_capture_rejection_count >= 1
    assert result.king_risk_rejection_count >= 1
    assert result.material_loss_rejection_count >= 1
    assert result.evidence["rejects_bad_capture"] is True
    assert result.evidence["rejects_king_risk"] is True
    assert result.evidence["rejects_material_loss"] is True


def test_phase22b24_emits_search_trace_hash(tmp_path):
    result = run_full_chess_basic_search_engine_kernel(
        memory_path=tmp_path / "basic_search_memory.json"
    )

    assert len(result.search_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b24_persists_search_memory(tmp_path):
    memory_path = tmp_path / "basic_search_memory.json"

    first = run_full_chess_basic_search_engine_kernel(memory_path=memory_path)
    second = run_full_chess_basic_search_engine_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_search_policy["kernel_run_count"] >= 2
    assert second.final_search_policy["basic_search_count"] >= 2
    assert second.final_search_policy["evaluated_node_count"] >= 20
    assert second.final_search_policy["selected_move_count"] >= 2
    assert memory_path.exists()
