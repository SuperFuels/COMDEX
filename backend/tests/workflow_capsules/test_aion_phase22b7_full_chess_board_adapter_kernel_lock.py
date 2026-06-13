from backend.modules.aion_games import run_full_chess_board_adapter_kernel


def test_phase22b7_builds_full_8x8_start_position(tmp_path):
    result = run_full_chess_board_adapter_kernel(memory_path=tmp_path / "full_chess_memory.json")

    assert result.kernel_version == "phase22b7_full_chess_board_adapter_kernel_v1"
    assert result.board_size == 8
    assert result.initial_piece_count == 32
    assert result.white_piece_count == 16
    assert result.black_piece_count == 16
    assert result.board_coordinates_valid is True
    assert result.standard_start_position is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b7_generates_standard_opening_moves(tmp_path):
    result = run_full_chess_board_adapter_kernel(memory_path=tmp_path / "full_chess_memory.json")

    assert result.legal_opening_move_count == 20
    assert result.pawn_opening_move_count == 16
    assert result.knight_opening_move_count == 4
    assert result.selected_move_legal is True
    assert result.selected_opening_move["piece_id"] == "W_PAWN_4"
    assert result.selected_opening_move["to_position"] == [4, 3]


def test_phase22b7_rejects_blocked_opening_pieces(tmp_path):
    result = run_full_chess_board_adapter_kernel(memory_path=tmp_path / "full_chess_memory.json")

    assert result.blocked_piece_rejection_count >= 4
    assert result.illegal_opening_move_count >= 4
    reasons = {m["reason"] for m in result.rejected_illegal_opening_moves}
    assert "path blocked by starting position" in reasons or "target occupied by own piece" in reasons


def test_phase22b7_persists_full_chess_memory(tmp_path):
    memory_path = tmp_path / "full_chess_memory.json"

    first = run_full_chess_board_adapter_kernel(memory_path=memory_path)
    second = run_full_chess_board_adapter_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_full_chess_policy["kernel_run_count"] >= 2
    assert second.final_full_chess_policy["full_board_grounding_count"] >= 2
    assert second.final_full_chess_policy["legal_opening_move_count"] >= 40
    assert memory_path.exists()
