import chess

from backend.modules.aion_games import run_full_chess_sqi_evaluation_bridge_kernel


def test_phase22d1_sqi_bridge_scores_start_position(tmp_path):
    result = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    legal = {move.uci() for move in chess.Board().legal_moves}

    assert result.kernel_version == "phase22d1_full_chess_sqi_evaluation_bridge_kernel_v1"
    assert result.bridge_mode == "sqi_chess_evaluation_bridge"
    assert result.sqi_enabled is True
    assert result.selected_move in legal
    assert result.candidate_count > 0
    assert result.selected_collapse_weight >= 0


def test_phase22d1_emits_sqi_metrics(tmp_path):
    result = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    top = result.top_sqi_candidates[0]

    assert "coherence_score" in top
    assert "resonance_score" in top
    assert "decoherence_penalty" in top
    assert "collapse_weight" in top
    assert "sqi_adjusted_score" in top
    assert result.coherence_mean > 0
    assert result.collapse_weight_total > 0


def test_phase22d1_selected_move_is_sqi_adjusted_best(tmp_path):
    result = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.selected_move == result.top_sqi_candidates[0]["move"]
    assert result.selected_sqi_adjusted_score == result.top_sqi_candidates[0]["sqi_adjusted_score"]
    assert result.selected_sqi_reason.startswith("sqi_")


def test_phase22d1_memory_persists(tmp_path):
    memory_path = tmp_path / "sqi_memory.json"

    first = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=memory_path,
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )
    second = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=memory_path,
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_sqi_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d1_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert len(result.sqi_trace_hash) == 64


def test_phase22d1_boundary_statement_is_honest(tmp_path):
    result = run_full_chess_sqi_evaluation_bridge_kernel(
        memory_path=tmp_path / "sqi_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
    )

    assert "operational SQI bridge" in result.boundary_statement
    assert "does not yet invoke physical wave hardware" in result.boundary_statement
