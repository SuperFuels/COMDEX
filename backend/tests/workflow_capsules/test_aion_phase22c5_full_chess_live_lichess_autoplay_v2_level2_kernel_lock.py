from backend.modules.aion_games import run_full_chess_live_lichess_autoplay_v2_level2_kernel


def test_phase22c5_targets_lichess_stockfish_level_2(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.kernel_version == "phase22c5_full_chess_live_lichess_autoplay_v2_level2_kernel_v1"
    assert result.platform == "lichess"
    assert result.account_id == "peekoo123"
    assert result.opponent_type == "lichess_ai_stockfish"
    assert result.opponent_level == 2
    assert result.evidence["target_is_stockfish_level_2"] is True


def test_phase22c5_uses_search_selector_adapter(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.selected_opening_move
    assert result.selected_opening_move_source == "phase22c3_depth_limited_search_selector"
    assert result.selected_opening_move_is_legal is True
    assert result.live_loop_ready is True
    assert result.evidence["search_selector_adapter_used"] is True
    assert result.evidence["old_heuristic_picker_replaced"] is True


def test_phase22c5_default_is_dry_run_and_no_network(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.dry_run is True
    assert result.network_enabled is False
    assert result.network_challenge_attempted is False
    assert result.network_move_send_attempted is False
    assert result.evidence["network_call_performed"] is False


def test_phase22c5_live_requires_token_and_explicit_network(tmp_path):
    dry_result = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        dry_run=True,
        network_enabled=True,
        token_present=True,
    )

    live_authorised_shape = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=tmp_path / "autoplay_memory_2.json",
        adapter_memory_path=tmp_path / "adapter_memory_2.json",
        search_memory_path=tmp_path / "search_memory_2.json",
        evaluation_memory_path=tmp_path / "evaluation_memory_2.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        dry_run=False,
        network_enabled=True,
        token_present=True,
    )

    assert dry_result.network_challenge_attempted is False
    assert live_authorised_shape.network_challenge_attempted is True
    assert live_authorised_shape.token_required_for_live is True
    assert live_authorised_shape.token_present is True


def test_phase22c5_persists_memory(tmp_path):
    memory_path = tmp_path / "autoplay_memory.json"

    first = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=memory_path,
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=memory_path,
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_autoplay_policy["kernel_run_count"] >= 2
    assert second.final_autoplay_policy["autoplay_plan_count"] >= 2
    assert memory_path.exists()


def test_phase22c5_no_external_side_effects_or_llm(tmp_path):
    result = run_full_chess_live_lichess_autoplay_v2_level2_kernel(
        memory_path=tmp_path / "autoplay_memory.json",
        adapter_memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish_local_engine"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["no_payment_created"] is True
    assert result.evidence["no_booking_created"] is True
    assert result.evidence["no_chain_write"] is True
    assert len(result.adapter_trace_hash) == 64
