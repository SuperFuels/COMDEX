from backend.modules.aion_games import run_full_chess_real_lichess_level2_sqi_game_loop_kernel


def test_phase22d6_dry_run_default_no_network_attempt(tmp_path):
    result = run_full_chess_real_lichess_level2_sqi_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.kernel_version == "phase22d6_real_lichess_level2_sqi_game_loop_kernel_v1"
    assert result.dry_run is True
    assert result.live_authorised is False
    assert result.challenge_attempted is False
    assert result.stream_attempted is False
    assert result.move_send_attempt_count == 0
    assert result.final_status == "not_started"


def test_phase22d6_dry_run_still_selects_sqi_opening(tmp_path):
    result = run_full_chess_real_lichess_level2_sqi_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.opponent_level == 2
    assert result.last_selected_move == "d2d4"
    assert result.last_selected_sqi_adjusted_score > 0
    assert len(result.last_sqi_trace_hash) == 64
    assert len(result.last_selection_trace_hash) == 64


def test_phase22d6_requires_all_live_gates(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_LICHESS_LIVE", raising=False)

    result = run_full_chess_real_lichess_level2_sqi_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        dry_run=False,
        network_enabled=True,
        token_value="test-token",
    )

    assert result.token_present is True
    assert result.live_env_enabled is False
    assert result.live_authorised is False
    assert result.challenge_attempted is False


def test_phase22d6_memory_persists(tmp_path):
    memory_path = tmp_path / "loop_memory.json"

    first = run_full_chess_real_lichess_level2_sqi_game_loop_kernel(
        memory_path=memory_path,
        sqi_live_adapter_memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_real_lichess_level2_sqi_game_loop_kernel(
        memory_path=memory_path,
        sqi_live_adapter_memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_loop_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d6_no_external_side_effects_in_dry_run(tmp_path):
    result = run_full_chess_real_lichess_level2_sqi_game_loop_kernel(
        memory_path=tmp_path / "loop_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish_local_engine"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert result.evidence["no_payment_created"] is True
    assert result.evidence["no_booking_created"] is True
    assert result.evidence["no_chain_write"] is True
    assert len(result.loop_trace_hash) == 64
