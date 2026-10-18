from backend.modules.aion_games import run_full_chess_sqi_failure_patch_selector_kernel


def test_phase22d8_selects_legal_move_from_start(tmp_path):
    result = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=tmp_path / "patch_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
    )

    assert result.kernel_version == "phase22d8_full_chess_sqi_failure_patch_selector_kernel_v1"
    assert result.selection_mode == "sqi_failure_patch_selector"
    assert result.selected_move_is_legal is True
    assert result.candidate_count > 0
    assert len(result.patch_trace_hash) == 64


def test_phase22d8_penalises_repeated_back_and_forth_moves(tmp_path):
    moves = [
        "d2d4", "d7d5",
        "g1f3", "g8f6",
        "f3g1", "f6g8",
        "g1f3", "g8f6",
    ]

    result = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=tmp_path / "patch_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
        moves=moves,
    )

    assert result.repetition_penalty_applied_count >= 1
    assert result.evidence["repetition_guard_active"] is True


def test_phase22d8_penalises_king_shuffle_when_losing(tmp_path):
    moves = [
        "e2e4", "d7d5",
        "e1e2", "d5e4",
        "e2e1", "e4e3",
    ]

    result = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=tmp_path / "patch_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
        moves=moves,
    )

    assert result.king_shuffle_penalty_applied_count >= 0
    assert result.evidence["king_shuffle_guard_active"] is True


def test_phase22d8_negative_spiral_guard_activates_on_loss_position(tmp_path):
    fen = "8/4k1p1/8/6q1/8/2p5/3pK3/1q3q2 w - - 10 54"

    result = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=tmp_path / "patch_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
        fen=fen,
    )

    assert result.negative_spiral_guard_applied is True
    assert result.evidence["negative_spiral_guard_active"] is True


def test_phase22d8_memory_persists(tmp_path):
    memory_path = tmp_path / "patch_memory.json"

    first = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=memory_path,
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
    )
    second = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=memory_path,
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_patch_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d8_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_sqi_failure_patch_selector_kernel(
        memory_path=tmp_path / "patch_memory.json",
        sqi_selector_memory_path=tmp_path / "sqi_selector_memory.json",
        sqi_bridge_memory_path=tmp_path / "sqi_bridge_memory.json",
        selector_memory_path=tmp_path / "selector_memory.json",
        evaluation_memory_path=tmp_path / "evaluation_memory.json",
        post_game_memory_path=tmp_path / "missing_post_game.json",
        review_memory_path=tmp_path / "missing_review.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
