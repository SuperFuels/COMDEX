from backend.modules.aion_games import run_full_chess_capture_evaluation_kernel


def test_phase22b11_scores_and_selects_safe_capture(tmp_path):
    result = run_full_chess_capture_evaluation_kernel(memory_path=tmp_path / "capture_memory.json")

    assert result.kernel_version == "phase22b11_full_chess_capture_evaluation_kernel_v1"
    assert result.board_size == 8
    assert result.capture_candidate_count >= 5
    assert result.safe_capture_count >= 1
    assert result.selected_capture_safe is True
    assert result.selected_capture_profitable is True
    assert result.selected_capture["move_id"] == "CAP-1"
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b11_rejects_bad_exchange_and_hanging_trap(tmp_path):
    result = run_full_chess_capture_evaluation_kernel(memory_path=tmp_path / "capture_memory.json")

    assert result.bad_exchange_rejection_count >= 1
    assert result.hanging_piece_trap_rejection_count >= 1
    assert result.avoided_bad_exchange is True
    assert result.avoided_hanging_piece_trap is True
    assert result.evidence["rejects_bad_exchange"] is True
    assert result.evidence["rejects_hanging_piece_trap"] is True


def test_phase22b11_rejects_king_exposure_blocked_capture_and_tracks_defence(tmp_path):
    result = run_full_chess_capture_evaluation_kernel(memory_path=tmp_path / "capture_memory.json")

    assert result.king_exposure_rejection_count >= 1
    assert result.blocked_capture_rejection_count >= 1
    assert result.defended_target_count >= 1
    assert result.preserved_king_safety is True
    assert result.evidence["rejects_king_exposure_capture"] is True
    assert result.evidence["rejects_blocked_capture"] is True
    assert result.evidence["detects_defended_targets"] is True
    assert len(result.capture_trace_hash) == 64


def test_phase22b11_persists_capture_evaluation_memory(tmp_path):
    memory_path = tmp_path / "capture_memory.json"

    first = run_full_chess_capture_evaluation_kernel(memory_path=memory_path)
    second = run_full_chess_capture_evaluation_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_capture_policy["kernel_run_count"] >= 2
    assert second.final_capture_policy["safe_capture_selection_count"] >= 2
    assert second.final_capture_policy["bad_exchange_rejection_count"] >= 2
    assert second.final_capture_policy["hanging_piece_trap_rejection_count"] >= 2
    assert second.final_capture_policy["blocked_capture_rejection_count"] >= 2
    assert memory_path.exists()
