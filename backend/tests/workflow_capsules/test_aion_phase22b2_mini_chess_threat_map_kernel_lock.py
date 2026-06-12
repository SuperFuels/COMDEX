from backend.modules.aion_games import run_mini_chess_threat_map_kernel


def test_phase22b2_detects_check_and_escape_moves(tmp_path):
    result = run_mini_chess_threat_map_kernel(memory_path=tmp_path / "threat_map_memory.json")

    assert result.kernel_version == "phase22b2_mini_chess_threat_map_kernel_v1"
    assert result.white_in_check is True
    assert result.detected_check is True
    assert result.checking_pieces
    assert result.found_escape_from_check is True
    assert result.legal_escape_moves
    assert result.selected_move["legal"] is True
    assert result.selected_move["exposes_king"] is False
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b2_maps_attacked_and_defended_squares(tmp_path):
    result = run_mini_chess_threat_map_kernel(memory_path=tmp_path / "threat_map_memory.json")

    assert result.attacked_squares["black"]
    assert result.attacked_squares["white"]
    assert "W_K" in result.defended_pieces
    assert isinstance(result.undefended_pieces, list)
    assert result.evidence["uses_attacked_square_map"] is True
    assert result.evidence["uses_defended_piece_map"] is True


def test_phase22b2_rejects_unsafe_capture_and_tracks_checking_moves(tmp_path):
    result = run_mini_chess_threat_map_kernel(memory_path=tmp_path / "threat_map_memory.json")

    assert result.unsafe_captures
    assert result.avoided_unsafe_capture is True
    assert result.checking_moves
    assert result.evidence["uses_unsafe_capture_detection"] is True
    assert result.evidence["uses_checking_move_detection"] is True


def test_phase22b2_persists_threat_map_memory(tmp_path):
    memory_path = tmp_path / "threat_map_memory.json"

    first = run_mini_chess_threat_map_kernel(memory_path=memory_path)
    second = run_mini_chess_threat_map_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_threat_map_policy["kernel_run_count"] >= 2
    assert second.final_threat_map_policy["check_detection_count"] >= 2
    assert second.final_threat_map_policy["escape_found_count"] >= 2
    assert "check_detection" in second.final_threat_map_policy["known_threat_concepts"]
    assert memory_path.exists()
