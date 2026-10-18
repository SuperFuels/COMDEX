from backend.modules.aion_games import run_full_chess_level2_sqi_loss_post_game_review_kernel


def test_phase22d7_reviews_real_level2_loss(tmp_path):
    result = run_full_chess_level2_sqi_loss_post_game_review_kernel(
        memory_path=tmp_path / "review_memory.json",
    )

    assert result.kernel_version == "phase22d7_full_chess_level2_sqi_loss_post_game_review_kernel_v1"
    assert result.game_id == "lynbgdRG"
    assert result.full_id == "lynbgdRGhRSF"
    assert result.opponent_level == 2
    assert result.final_status == "mate"
    assert result.winner == "black"
    assert result.aion_result == "loss"
    assert result.final_move == "f5f1"


def test_phase22d7_detects_failure_modes(tmp_path):
    result = run_full_chess_level2_sqi_loss_post_game_review_kernel(
        memory_path=tmp_path / "review_memory.json",
    )

    assert result.repeated_cycle_count > 0
    assert result.king_shuffle_count >= 10
    assert result.queen_invasion_detected is True
    assert result.rook_invasion_detected is True
    assert result.promotion_allowed is True
    assert result.forced_mate_missed is True
    assert result.negative_sqi_spiral_detected is True


def test_phase22d7_generates_policy_updates(tmp_path):
    result = run_full_chess_level2_sqi_loss_post_game_review_kernel(
        memory_path=tmp_path / "review_memory.json",
    )

    assert result.policy_updates["block_repetition_loops"] is True
    assert result.policy_updates["raise_king_safety_weight_when_losing"] is True
    assert result.policy_updates["detect_queen_rook_invasion"] is True
    assert result.policy_updates["detect_promotion_race_threats"] is True
    assert result.policy_updates["stand_down_from_bad_sqi_collapse_when_all_candidates_negative"] is True
    assert result.policy_updates["next_selector_patch"] == "22D.8 -- Patch SQI Selector Against Level 2 Failure Modes"


def test_phase22d7_memory_persists(tmp_path):
    memory_path = tmp_path / "review_memory.json"

    first = run_full_chess_level2_sqi_loss_post_game_review_kernel(memory_path=memory_path)
    second = run_full_chess_level2_sqi_loss_post_game_review_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_review_policy["kernel_run_count"] >= 2
    assert memory_path.exists()


def test_phase22d7_no_external_engine_or_llm(tmp_path):
    result = run_full_chess_level2_sqi_loss_post_game_review_kernel(
        memory_path=tmp_path / "review_memory.json",
    )

    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_stockfish"] is False
    assert result.evidence["uses_cloud_engine"] is False
    assert result.evidence["uses_lichess_analysis"] is False
    assert len(result.review_trace_hash) == 64
