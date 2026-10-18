from backend.modules.aion_games import run_full_chess_playable_ui_kernel


def test_phase22b27_emits_playable_ui_state(tmp_path):
    result = run_full_chess_playable_ui_kernel(
        memory_path=tmp_path / "playable_ui_memory.json"
    )

    assert result.kernel_version == "phase22b27_full_chess_playable_ui_kernel_v1"
    assert result.board_size == 8
    assert result.ui_status == "aion_response_ready"
    assert result.move_log_count == 2
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b27_accepts_user_move_and_applies_board_update(tmp_path):
    result = run_full_chess_playable_ui_kernel(
        memory_path=tmp_path / "playable_ui_memory.json",
        user_uci_move="g8f6",
    )

    assert result.user_move_accepted is True
    assert result.board_updated_after_user_move is True
    assert result.playable_ui_state["move_log"][0]["actor"] == "user"
    assert result.playable_ui_state["move_log"][0]["uci_move"] == "g8f6"
    assert result.evidence["accepts_user_move"] is True
    assert result.evidence["applies_user_move"] is True


def test_phase22b27_selects_aion_response_and_exports_state(tmp_path):
    result = run_full_chess_playable_ui_kernel(
        memory_path=tmp_path / "playable_ui_memory.json"
    )

    assert result.selected_aion_uci_move == "c4d5"
    assert result.aion_response_ready is True
    assert result.board_updated_after_aion_move is True
    assert result.final_fen
    assert result.final_pgn == "1... Nf6 2. cxd5"
    assert result.evidence["exports_updated_fen"] is True
    assert result.evidence["exports_updated_pgn"] is True


def test_phase22b27_preserves_kings_and_trace_hash(tmp_path):
    result = run_full_chess_playable_ui_kernel(
        memory_path=tmp_path / "playable_ui_memory.json"
    )

    assert result.evidence["preserves_kings"] is True
    assert len(result.playable_ui_trace_hash) == 64
    assert result.playable_ui_state["ui_trace_hash"] == result.playable_ui_trace_hash
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b27_persists_playable_ui_memory(tmp_path):
    memory_path = tmp_path / "playable_ui_memory.json"

    first = run_full_chess_playable_ui_kernel(memory_path=memory_path)
    second = run_full_chess_playable_ui_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_playable_ui_policy["kernel_run_count"] >= 2
    assert second.final_playable_ui_policy["playable_ui_session_count"] >= 2
    assert second.final_playable_ui_policy["accepted_user_move_count"] >= 2
    assert second.final_playable_ui_policy["aion_response_count"] >= 2
    assert memory_path.exists()
