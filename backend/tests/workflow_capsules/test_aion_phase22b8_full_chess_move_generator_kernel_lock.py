from backend.modules.aion_games import run_full_chess_move_generator_kernel


def test_phase22b8_generates_full_chess_move_classes(tmp_path):
    result = run_full_chess_move_generator_kernel(memory_path=tmp_path / "move_memory.json")

    assert result.kernel_version == "phase22b8_full_chess_move_generator_kernel_v1"
    assert result.board_size == 8
    assert result.legal_move_count >= 6
    assert result.pawn_forward_move_count >= 1
    assert result.pawn_capture_move_count >= 2
    assert result.knight_move_count >= 1
    assert result.sliding_move_count >= 1
    assert result.king_move_count >= 1
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b8_rejects_illegal_moves_and_king_safety_risk(tmp_path):
    result = run_full_chess_move_generator_kernel(memory_path=tmp_path / "move_memory.json")

    assert result.illegal_move_count >= 3
    assert result.blocked_path_rejection_count >= 1
    assert result.own_piece_rejection_count >= 1
    assert result.king_safety_rejection_count >= 1
    assert result.evidence["rejects_blocked_paths"] is True
    assert result.evidence["rejects_own_piece_targets"] is True
    assert result.evidence["uses_king_safety_filter"] is True


def test_phase22b8_selects_legal_pawn_capture(tmp_path):
    result = run_full_chess_move_generator_kernel(memory_path=tmp_path / "move_memory.json")

    assert result.selected_move_legal is True
    assert result.selected_move["move_id"] == "M-PC-1"
    assert result.selected_move["move_type"] == "capture"
    assert result.selected_move_reason == "legal pawn capture"
    assert len(result.full_chess_move_trace_hash) == 64


def test_phase22b8_persists_move_generator_memory(tmp_path):
    memory_path = tmp_path / "move_memory.json"

    first = run_full_chess_move_generator_kernel(memory_path=memory_path)
    second = run_full_chess_move_generator_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_move_generator_policy["kernel_run_count"] >= 2
    assert second.final_move_generator_policy["legal_move_generation_count"] >= 12
    assert second.final_move_generator_policy["illegal_move_rejection_count"] >= 6
    assert memory_path.exists()
