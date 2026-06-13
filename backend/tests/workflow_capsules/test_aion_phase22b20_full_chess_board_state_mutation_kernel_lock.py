from backend.modules.aion_games import run_full_chess_board_state_mutation_kernel


def test_phase22b20_applies_real_board_mutation(tmp_path):
    result = run_full_chess_board_state_mutation_kernel(
        memory_path=tmp_path / "board_mutation_memory.json"
    )

    assert result.kernel_version == "phase22b20_full_chess_board_state_mutation_kernel_v1"
    assert result.board_size == 8
    assert len(result.board_before) == 8
    assert len(result.board_after) == 8
    assert result.mutation_applied is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b20_clears_origin_and_fills_target(tmp_path):
    result = run_full_chess_board_state_mutation_kernel(
        memory_path=tmp_path / "board_mutation_memory.json"
    )

    assert result.move["from_square"] == "C4"
    assert result.move["to_square"] == "D5"
    assert result.origin_cleared is True
    assert result.target_occupied_by_moved_piece is True
    assert result.board_after[4][2] == "__"
    assert result.board_after[3][3] == "W_P"


def test_phase22b20_removes_captured_piece_and_changes_count(tmp_path):
    result = run_full_chess_board_state_mutation_kernel(
        memory_path=tmp_path / "board_mutation_memory.json"
    )

    assert result.captured_piece_removed is True
    assert result.piece_count_after == result.piece_count_before - 1
    assert "B_N_TARGET" not in [piece for row in result.board_after for piece in row]


def test_phase22b20_changes_board_hash_and_preserves_king(tmp_path):
    result = run_full_chess_board_state_mutation_kernel(
        memory_path=tmp_path / "board_mutation_memory.json"
    )

    assert result.board_hash_before != result.board_hash_after
    assert result.board_hash_changed is True
    assert result.king_safe_after_move is True
    assert len(result.mutation_trace_hash) == 64


def test_phase22b20_persists_board_mutation_memory(tmp_path):
    memory_path = tmp_path / "board_mutation_memory.json"

    first = run_full_chess_board_state_mutation_kernel(memory_path=memory_path)
    second = run_full_chess_board_state_mutation_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_board_mutation_policy["kernel_run_count"] >= 2
    assert second.final_board_mutation_policy["mutation_count"] >= 2
    assert second.final_board_mutation_policy["capture_mutation_count"] >= 2
    assert memory_path.exists()
