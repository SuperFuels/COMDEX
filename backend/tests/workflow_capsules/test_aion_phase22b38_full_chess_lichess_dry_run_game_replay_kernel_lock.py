from backend.modules.aion_games import run_full_chess_lichess_dry_run_game_replay_kernel


def test_phase22b38_replays_lichess_dry_run_events(tmp_path):
    result = run_full_chess_lichess_dry_run_game_replay_kernel(
        memory_path=tmp_path / "dry_run_replay_memory.json"
    )

    assert result.kernel_version == "phase22b38_full_chess_lichess_dry_run_game_replay_kernel_v1"
    assert result.replay_mode == "offline_lichess_dry_run_game_replay"
    assert result.dry_run is True
    assert result.network_call_performed is False
    assert result.human_approval_required is False
    assert result.event_count == 2
    assert result.replayed_event_count == 2
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b38_detects_aion_turn_and_selects_move(tmp_path):
    result = run_full_chess_lichess_dry_run_game_replay_kernel(
        memory_path=tmp_path / "dry_run_replay_memory.json"
    )

    assert result.aion_colour == "white"
    assert result.aion_turn_detected is True
    assert result.selected_bestmove == "c2c4"
    assert result.selected_policy == "KNOWLEDGE-GUIDED-ENGLISH-OPENING-SAFE-DEVELOPMENT"
    assert result.evidence["detects_aion_turn"] is True
    assert result.evidence["selects_knowledge_guided_move"] is True


def test_phase22b38_prepares_move_payload_without_network(tmp_path):
    result = run_full_chess_lichess_dry_run_game_replay_kernel(
        memory_path=tmp_path / "dry_run_replay_memory.json"
    )

    assert result.would_post_move is True
    assert result.prepared_move_url.endswith("/move/c2c4")
    assert result.replay_decision["prepared_payload"]["move"] == "c2c4"
    assert result.replay_decision["network_call_performed"] is False
    assert result.evidence["blocks_network_call"] is True


def test_phase22b38_emits_trace_hash(tmp_path):
    result = run_full_chess_lichess_dry_run_game_replay_kernel(
        memory_path=tmp_path / "dry_run_replay_memory.json"
    )

    assert len(result.dry_run_replay_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b38_persists_replay_memory(tmp_path):
    memory_path = tmp_path / "dry_run_replay_memory.json"

    first = run_full_chess_lichess_dry_run_game_replay_kernel(memory_path=memory_path)
    second = run_full_chess_lichess_dry_run_game_replay_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_dry_run_replay_policy["kernel_run_count"] >= 2
    assert second.final_dry_run_replay_policy["dry_run_replay_session_count"] >= 2
    assert second.final_dry_run_replay_policy["replayed_event_total"] >= 4
    assert memory_path.exists()
