from backend.modules.aion_games import run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel


def test_phase22d5_dry_run_default_no_network_attempt(tmp_path):
    result = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=tmp_path / "runner_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.kernel_version == "phase22d5_real_lichess_level2_sqi_autoplay_runner_kernel_v1"
    assert result.dry_run is True
    assert result.network_enabled is False
    assert result.live_authorised is False
    assert result.challenge_attempted is False
    assert result.move_send_attempted is False
    assert result.final_status == "not_started"


def test_phase22d5_targets_level2_and_uses_sqi_selector(tmp_path):
    result = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=tmp_path / "runner_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.platform == "lichess"
    assert result.account_id == "peekoo123"
    assert result.opponent_level == 2
    assert result.selected_opening_move == "d2d4"
    assert result.selected_opening_move_source == "phase22d2_sqi_guided_move_selection"
    assert result.selected_opening_move_is_legal is True
    assert result.evidence["sqi_guided_selector_used"] is True


def test_phase22d5_requires_all_live_gates(tmp_path, monkeypatch):
    monkeypatch.delenv("AION_LICHESS_LIVE", raising=False)

    result = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=tmp_path / "runner_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
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


def test_phase22d5_live_authorised_shape_without_call_when_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LICHESS_LIVE", "1")

    result = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=tmp_path / "runner_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        dry_run=True,
        network_enabled=True,
        token_value="test-token",
    )

    assert result.live_env_enabled is True
    assert result.token_present is True
    assert result.live_authorised is False
    assert result.challenge_attempted is False


def test_phase22d5_memory_persists(tmp_path):
    memory_path = tmp_path / "runner_memory.json"

    first = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=memory_path,
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=memory_path,
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_runner_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d5_no_external_side_effects_in_dry_run(tmp_path):
    result = run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel(
        memory_path=tmp_path / "runner_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
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
    assert len(result.runner_trace_hash) == 64
