from backend.modules.aion_games import run_mini_chess_legal_move_kernel


def test_phase22b1_generates_legal_and_illegal_moves(tmp_path):
    result = run_mini_chess_legal_move_kernel(memory_path=tmp_path / "mini_chess_memory.json")

    assert result.kernel_version == "phase22b1_mini_chess_legal_move_kernel_v1"
    assert result.board_size == 4
    assert result.legal_move_count >= 2
    assert result.illegal_move_count >= 2
    assert result.capture_move_count >= 1
    assert result.avoided_illegal_move is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b1_selects_safe_capture_and_preserves_king(tmp_path):
    result = run_mini_chess_legal_move_kernel(memory_path=tmp_path / "mini_chess_memory.json")

    assert result.selected_move["legal"] is True
    assert result.selected_move["move_type"] == "capture"
    assert result.selected_move["capture_target"] == "B_N"
    assert result.selected_safe_capture is True
    assert result.avoided_exposing_king is True
    assert result.selected_move["exposes_king"] is False


def test_phase22b1_tracks_threat_map_and_trace_hash(tmp_path):
    result = run_mini_chess_legal_move_kernel(memory_path=tmp_path / "mini_chess_memory.json")

    assert "white_king_position" in result.threat_map
    assert "black_threatens" in result.threat_map
    assert len(result.board_trace_hash) == 64
    assert result.evidence["uses_threat_map"] is True
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b1_persists_mini_chess_memory(tmp_path):
    memory_path = tmp_path / "mini_chess_memory.json"

    first = run_mini_chess_legal_move_kernel(memory_path=memory_path)
    second = run_mini_chess_legal_move_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_mini_chess_policy["kernel_run_count"] >= 2
    assert second.final_mini_chess_policy["safe_capture_count"] >= 2
    assert "knight" in second.final_mini_chess_policy["known_piece_rules"]
    assert memory_path.exists()
