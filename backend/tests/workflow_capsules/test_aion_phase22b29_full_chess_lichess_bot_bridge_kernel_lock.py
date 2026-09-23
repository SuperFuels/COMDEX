from backend.modules.aion_games import run_full_chess_lichess_bot_bridge_kernel


def test_phase22b29_accepts_lichess_events(tmp_path):
    result = run_full_chess_lichess_bot_bridge_kernel(
        memory_path=tmp_path / "lichess_bridge_memory.json"
    )

    assert result.kernel_version == "phase22b29_full_chess_lichess_bot_bridge_kernel_v1"
    assert result.bridge_mode == "offline_lichess_bot_bridge_contract"
    assert result.event_count == 2
    assert result.accepted_event_count == 2
    assert result.challenge_event_accepted is True
    assert result.game_state_event_accepted is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b29_extracts_game_state(tmp_path):
    result = run_full_chess_lichess_bot_bridge_kernel(
        memory_path=tmp_path / "lichess_bridge_memory.json"
    )

    assert result.game_id == "aion-demo-game-001"
    assert result.bot_colour == "white"
    assert result.side_to_move == "white"
    assert result.input_fen
    assert result.evidence["extracts_game_id"] is True
    assert result.evidence["extracts_fen"] is True
    assert result.evidence["extracts_side_to_move"] is True


def test_phase22b29_builds_move_payload(tmp_path):
    result = run_full_chess_lichess_bot_bridge_kernel(
        memory_path=tmp_path / "lichess_bridge_memory.json"
    )

    assert result.selected_bestmove == "c4d5"
    assert result.lichess_move_payload["game_id"] == result.game_id
    assert result.lichess_move_payload["move"] == "c4d5"
    assert result.lichess_move_payload["source"] == "aion_uci_bestmove"
    assert result.response_ready is True
    assert result.should_resign is False
    assert result.evidence["builds_lichess_move_payload"] is True


def test_phase22b29_emits_trace_hash(tmp_path):
    result = run_full_chess_lichess_bot_bridge_kernel(
        memory_path=tmp_path / "lichess_bridge_memory.json"
    )

    assert len(result.lichess_bridge_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b29_persists_bridge_memory(tmp_path):
    memory_path = tmp_path / "lichess_bridge_memory.json"

    first = run_full_chess_lichess_bot_bridge_kernel(memory_path=memory_path)
    second = run_full_chess_lichess_bot_bridge_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_lichess_bridge_policy["kernel_run_count"] >= 2
    assert second.final_lichess_bridge_policy["lichess_bridge_session_count"] >= 2
    assert second.final_lichess_bridge_policy["move_payload_count"] >= 2
    assert memory_path.exists()
