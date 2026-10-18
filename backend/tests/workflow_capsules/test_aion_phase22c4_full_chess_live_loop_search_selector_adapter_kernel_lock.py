import chess

from backend.modules.aion_games import run_full_chess_live_loop_search_selector_adapter_kernel


def test_phase22c4_selects_search_move_when_aion_turn(tmp_path):
    result = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
        search_depth_limit=2,
    )

    legal = {move.uci() for move in chess.Board().legal_moves}

    assert result.kernel_version == "phase22c4_full_chess_live_loop_search_selector_adapter_kernel_v1"
    assert result.adapter_mode == "live_loop_search_selector_adapter"
    assert result.is_aion_turn is True
    assert result.selected_move in legal
    assert result.live_loop_move_source == "phase22c3_depth_limited_search_selector"
    assert result.old_heuristic_picker_replaced is True


def test_phase22c4_skips_when_not_aion_turn(tmp_path):
    result = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="black",
        moves=[],
        search_depth_limit=2,
    )

    assert result.is_aion_turn is False
    assert result.selected_move == ""
    assert result.selected_reason == "not_aion_turn"
    assert result.evidence["no_move_when_not_aion_turn"] is True


def test_phase22c4_skips_terminal_position(tmp_path):
    board = chess.Board()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        board.push_uci(move)

    result = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        fen=board.fen(),
        search_depth_limit=2,
    )

    assert result.terminal_position is True
    assert result.selected_move == ""
    assert result.selected_reason == "terminal_position_no_move"
    assert result.evidence["no_move_when_terminal"] is True


def test_phase22c4_does_not_send_network_move_in_this_phase(tmp_path):
    result = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
        dry_run=True,
        network_send_allowed=False,
    )

    assert result.dry_run is True
    assert result.network_send_allowed is False
    assert result.network_send_attempted is False
    assert result.evidence["network_call_performed"] is False


def test_phase22c4_persists_memory(tmp_path):
    memory_path = tmp_path / "adapter_memory.json"

    first = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=memory_path,
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )
    second = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=memory_path,
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_adapter_policy["kernel_run_count"] >= 2
    assert second.final_adapter_policy["adapter_invocation_count"] >= 2
    assert memory_path.exists()


def test_phase22c4_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_live_loop_search_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        search_memory_path=tmp_path / "search_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert len(result.adapter_trace_hash) == 64
