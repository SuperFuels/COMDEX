from backend.modules.aion_games import run_full_chess_live_lichess_bot_connector_kernel


def test_phase22b30_builds_dry_run_connector_config(tmp_path):
    result = run_full_chess_live_lichess_bot_connector_kernel(
        memory_path=tmp_path / "live_lichess_connector_memory.json"
    )

    assert result.kernel_version == "phase22b30_full_chess_live_lichess_bot_connector_kernel_v1"
    assert result.connector_mode == "dry_run_live_lichess_connector_contract"
    assert result.config["bot_token_env_name"] == "LICHESS_BOT_TOKEN"
    assert result.config["dry_run"] is True
    assert result.config["allow_network"] is False
    assert result.dry_run_guard_active is True
    assert result.network_call_performed is False
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b30_builds_lichess_endpoints(tmp_path):
    result = run_full_chess_live_lichess_bot_connector_kernel(
        memory_path=tmp_path / "live_lichess_connector_memory.json"
    )

    assert result.endpoints["event_stream_url"] == "https://lichess.org/api/stream/event"
    assert result.game_id in result.endpoints["game_stream_url"]
    assert result.selected_bestmove in result.endpoints["bot_move_url"]
    assert result.endpoints["method_for_move"] == "POST"
    assert result.evidence["builds_event_stream_endpoint"] is True
    assert result.evidence["builds_game_stream_endpoint"] is True
    assert result.evidence["builds_bot_move_endpoint"] is True


def test_phase22b30_prepares_move_payload_without_network_call(tmp_path):
    result = run_full_chess_live_lichess_bot_connector_kernel(
        memory_path=tmp_path / "live_lichess_connector_memory.json"
    )

    assert result.lichess_move_payload["game_id"] == "aion-demo-game-001"
    assert result.lichess_move_payload["move"] == "c4d5"
    assert result.lichess_move_payload["method"] == "POST"
    assert result.would_post_move is True
    assert result.network_call_performed is False
    assert result.connector_ready is True
    assert result.evidence["does_not_perform_network_call"] is True


def test_phase22b30_emits_trace_hash(tmp_path):
    result = run_full_chess_live_lichess_bot_connector_kernel(
        memory_path=tmp_path / "live_lichess_connector_memory.json"
    )

    assert len(result.live_connector_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b30_persists_connector_memory(tmp_path):
    memory_path = tmp_path / "live_lichess_connector_memory.json"

    first = run_full_chess_live_lichess_bot_connector_kernel(memory_path=memory_path)
    second = run_full_chess_live_lichess_bot_connector_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_live_connector_policy["kernel_run_count"] >= 2
    assert second.final_live_connector_policy["live_connector_session_count"] >= 2
    assert second.final_live_connector_policy["dry_run_session_count"] >= 2
    assert second.final_live_connector_policy["prepared_move_payload_count"] >= 2
    assert memory_path.exists()
