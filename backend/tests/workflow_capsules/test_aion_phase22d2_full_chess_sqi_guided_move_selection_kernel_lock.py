import chess

from backend.modules.aion_games import run_full_chess_sqi_guided_move_selection_kernel


def test_phase22d2_selects_legal_move_using_sqi(tmp_path):
    result = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    legal = {move.uci() for move in chess.Board().legal_moves}

    assert result.kernel_version == "phase22d2_full_chess_sqi_guided_move_selection_kernel_v1"
    assert result.selection_mode == "sqi_guided_move_selection"
    assert result.selected_move in legal
    assert result.selected_move_is_legal is True
    assert result.evidence["selection_uses_sqi_adjusted_score"] is True


def test_phase22d2_preserves_classical_and_sqi_scores(tmp_path):
    result = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.selected_classical_score != 0
    assert result.selected_sqi_adjusted_score != 0
    assert result.selected_sqi_adjusted_score >= result.selected_classical_score
    assert result.selected_collapse_weight >= 0
    assert result.selected_sqi_reason.startswith("sqi_")


def test_phase22d2_selected_candidate_matches_top_sqi_candidate(tmp_path):
    result = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    top = result.top_sqi_candidates[0]

    assert result.selected_move == top["move"]
    assert result.selected_sqi_adjusted_score == top["sqi_adjusted_score"]
    assert result.selected_collapse_weight == top["collapse_weight"]


def test_phase22d2_live_loop_compatible(tmp_path):
    result = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.live_loop_compatible is True
    assert result.evidence["live_loop_compatible"] is True


def test_phase22d2_memory_persists(tmp_path):
    memory_path = tmp_path / "selection_memory.json"

    first = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=memory_path,
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=memory_path,
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_selection_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d2_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_sqi_guided_move_selection_kernel(
        memory_path=tmp_path / "selection_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert len(result.selection_trace_hash) == 64
    assert len(result.sqi_trace_hash) == 64
