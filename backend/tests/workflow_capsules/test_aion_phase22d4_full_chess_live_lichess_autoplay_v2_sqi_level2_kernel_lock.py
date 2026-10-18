from backend.modules.aion_games import run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel


def test_phase22d4_targets_level2_and_uses_sqi_selector(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.kernel_version == "phase22d4_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel_v1"
    assert result.platform == "lichess"
    assert result.account_id == "peekoo123"
    assert result.opponent_level == 2
    assert result.evidence["target_is_stockfish_level_2"] is True
    assert result.evidence["sqi_guided_selector_used"] is True


def test_phase22d4_selected_move_is_sqi_scored_and_legal(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.selected_opening_move == "d2d4"
    assert result.selected_opening_move_source == "phase22d2_sqi_guided_move_selection"
    assert result.selected_opening_move_is_legal is True
    assert result.selected_sqi_adjusted_score > result.selected_classical_score
    assert result.selected_collapse_weight > 0
    assert result.live_loop_ready is True


def test_phase22d4_default_is_dry_run_no_network(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.dry_run is True
    assert result.network_enabled is False
    assert result.network_challenge_attempted is False
    assert result.network_move_send_attempted is False
    assert result.evidence["network_call_performed"] is False


def test_phase22d4_live_requires_token_and_explicit_network(tmp_path):
    dry_result = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        dry_run=True,
        network_enabled=True,
        token_present=True,
    )

    live_shape = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=tmp_path / "autoplay_memory_2.json",
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory_2.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory_2.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory_2.json",
        selector_memory_path=tmp_path / "selector_memory_2.json",
        evaluation_memory_path=tmp_path / "evaluation_memory_2.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        dry_run=False,
        network_enabled=True,
        token_present=True,
    )

    assert dry_result.network_challenge_attempted is False
    assert live_shape.network_challenge_attempted is True
    assert live_shape.token_required_for_live is True
    assert live_shape.token_present is True


def test_phase22d4_memory_persists(tmp_path):
    memory_path = tmp_path / "autoplay_memory.json"

    first = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=memory_path,
        sqi_live_adapter_memory_path=tmp_path / "sqi_live_adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
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
    assert second.final_autoplay_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d4_no_external_side_effects_or_llm(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
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
    assert len(result.autoplay_trace_hash) == 64
    assert len(result.sqi_trace_hash) == 64
    assert len(result.selection_trace_hash) == 64
