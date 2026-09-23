from backend.modules.aion_games import run_full_chess_legal_move_safety_kernel


def test_phase22b10_filters_pseudo_legal_king_exposure(tmp_path):
    result = run_full_chess_legal_move_safety_kernel(memory_path=tmp_path / "safety_memory.json")

    assert result.kernel_version == "phase22b10_full_chess_legal_move_safety_kernel_v1"
    assert result.board_size == 8
    assert result.pseudo_legal_move_count >= 5
    assert result.safe_legal_move_count >= 1
    assert result.unsafe_king_exposure_count >= 1
    assert result.evidence["filters_king_exposure"] is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b10_rejects_illegal_move_classes(tmp_path):
    result = run_full_chess_legal_move_safety_kernel(memory_path=tmp_path / "safety_memory.json")

    assert result.own_piece_rejection_count >= 1
    assert result.illegal_geometry_count >= 1
    assert result.evidence["rejects_own_piece_targets"] is True
    assert result.evidence["rejects_illegal_geometry"] is True


def test_phase22b10_selects_safe_move_that_preserves_king(tmp_path):
    result = run_full_chess_legal_move_safety_kernel(memory_path=tmp_path / "safety_memory.json")

    assert result.selected_safe_move["safe_legal"] is True
    assert result.selected_move_preserves_king_safety is True
    assert result.king_safe_after_selected_move is True
    assert len(result.legal_safety_trace_hash) == 64


def test_phase22b10_persists_safety_memory(tmp_path):
    memory_path = tmp_path / "safety_memory.json"

    first = run_full_chess_legal_move_safety_kernel(memory_path=memory_path)
    second = run_full_chess_legal_move_safety_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_safety_policy["kernel_run_count"] >= 2
    assert second.final_safety_policy["safe_move_selection_count"] >= 2
    assert second.final_safety_policy["king_exposure_rejection_count"] >= 2
    assert memory_path.exists()
