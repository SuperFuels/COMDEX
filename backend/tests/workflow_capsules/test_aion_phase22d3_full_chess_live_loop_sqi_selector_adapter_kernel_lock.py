import chess

from backend.modules.aion_games import run_full_chess_live_loop_sqi_selector_adapter_kernel


def test_phase22d3_live_loop_uses_sqi_selector_when_aion_turn(tmp_path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )

    legal = {move.uci() for move in chess.Board().legal_moves}

    assert result.kernel_version == "phase22d3_full_chess_live_loop_sqi_selector_adapter_kernel_v1"
    assert result.adapter_mode == "live_loop_sqi_selector_adapter"
    assert result.is_aion_turn is True
    assert result.selected_move in legal
    assert result.live_loop_move_source == "phase22d2_sqi_guided_move_selection"
    assert result.sqi_guided_selector_used is True
    assert result.old_search_only_selector_replaced is True


def test_phase22d3_skips_when_not_aion_turn(tmp_path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="black",
        moves=[],
    )

    assert result.is_aion_turn is False
    assert result.selected_move == ""
    assert result.live_loop_move_source == "none"
    assert result.evidence["no_move_when_not_aion_turn"] is True


def test_phase22d3_skips_terminal_position(tmp_path):
    board = chess.Board()
    for move in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        board.push_uci(move)

    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        fen=board.fen(),
    )

    assert result.terminal_position is True
    assert result.selected_move == ""
    assert result.selected_sqi_reason == "terminal_position_no_move"
    assert result.evidence["no_move_when_terminal"] is True


def test_phase22d3_dry_run_no_network(tmp_path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
        dry_run=True,
        network_send_allowed=False,
    )

    assert result.dry_run is True
    assert result.network_send_attempted is False
    assert result.evidence["network_call_performed"] is False


def test_phase22d3_memory_persists(tmp_path):
    memory_path = tmp_path / "adapter_memory.json"

    first = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=memory_path,
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )
    second = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=memory_path,
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_adapter_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d3_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_live_loop_sqi_selector_adapter_kernel(
        memory_path=tmp_path / "adapter_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        aion_colour="white",
        moves=[],
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert len(result.adapter_trace_hash) == 64
    assert len(result.sqi_trace_hash) == 64
    assert len(result.selection_trace_hash) == 64
