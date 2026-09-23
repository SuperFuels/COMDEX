from backend.modules.aion_games import run_full_chess_threat_map_kernel


def test_phase22b9_detects_full_board_check(tmp_path):
    result = run_full_chess_threat_map_kernel(memory_path=tmp_path / "threat_memory.json")

    assert result.kernel_version == "phase22b9_full_chess_threat_map_kernel_v1"
    assert result.board_size == 8
    assert result.white_in_check is True
    assert result.detected_check is True
    assert "B_R" in result.checking_pieces
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b9_finds_legal_escape_and_rejects_unsafe_escape(tmp_path):
    result = run_full_chess_threat_map_kernel(memory_path=tmp_path / "threat_memory.json")

    assert result.found_escape_from_check is True
    assert len(result.legal_escape_moves) >= 1
    assert result.rejected_unsafe_escape is True
    assert len(result.rejected_unsafe_moves) >= 1
    assert result.evidence["finds_legal_escape"] is True
    assert result.evidence["rejects_unsafe_escape"] is True


def test_phase22b9_selects_checking_counter_move(tmp_path):
    result = run_full_chess_threat_map_kernel(memory_path=tmp_path / "threat_memory.json")

    assert result.selected_checking_counter_move is True
    assert result.selected_move["legal"] is True
    assert result.selected_move["escapes_check"] is True
    assert result.selected_move["creates_check"] is True
    assert len(result.threat_trace_hash) == 64


def test_phase22b9_persists_threat_memory(tmp_path):
    memory_path = tmp_path / "threat_memory.json"

    first = run_full_chess_threat_map_kernel(memory_path=memory_path)
    second = run_full_chess_threat_map_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_threat_policy["kernel_run_count"] >= 2
    assert second.final_threat_policy["check_detection_count"] >= 2
    assert second.final_threat_policy["escape_from_check_count"] >= 2
    assert second.final_threat_policy["checking_counter_move_count"] >= 2
    assert memory_path.exists()
