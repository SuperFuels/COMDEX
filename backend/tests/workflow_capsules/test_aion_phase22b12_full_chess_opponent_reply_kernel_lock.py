from backend.modules.aion_games import run_full_chess_opponent_reply_kernel


def test_phase22b12_generates_and_scores_opponent_replies(tmp_path):
    result = run_full_chess_opponent_reply_kernel(memory_path=tmp_path / "opponent_reply_memory.json")

    assert result.kernel_version == "phase22b12_full_chess_opponent_reply_kernel_v1"
    assert result.board_size == 8
    assert result.candidate_move_count >= 5
    assert result.opponent_reply_count >= 5
    assert result.safe_after_reply_count >= 1
    assert result.evidence["generates_opponent_replies"] is True
    assert result.evidence["scores_reply_material_loss"] is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b12_rejects_bad_replies_and_material_loss(tmp_path):
    result = run_full_chess_opponent_reply_kernel(memory_path=tmp_path / "opponent_reply_memory.json")

    assert result.bad_reply_rejection_count >= 1
    assert result.material_loss_reply_rejection_count >= 1
    assert result.avoided_bad_opponent_reply is True
    assert result.avoided_material_loss_reply is True
    assert result.evidence["rejects_bad_opponent_reply"] is True
    assert result.evidence["rejects_material_loss_reply"] is True


def test_phase22b12_rejects_king_exposure_and_selects_surviving_move(tmp_path):
    result = run_full_chess_opponent_reply_kernel(memory_path=tmp_path / "opponent_reply_memory.json")

    assert result.king_exposure_reply_rejection_count >= 1
    assert result.avoided_king_exposure_reply is True
    assert result.selected_move_survives_reply is True
    assert result.selected_move["move_id"] == "OR-1"
    assert result.selected_move_final_net_score >= 0
    assert len(result.opponent_reply_trace_hash) == 64
    assert result.evidence["selects_move_that_survives_reply"] is True


def test_phase22b12_persists_opponent_reply_memory(tmp_path):
    memory_path = tmp_path / "opponent_reply_memory.json"

    first = run_full_chess_opponent_reply_kernel(memory_path=memory_path)
    second = run_full_chess_opponent_reply_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_opponent_reply_policy["kernel_run_count"] >= 2
    assert second.final_opponent_reply_policy["safe_after_reply_selection_count"] >= 2
    assert second.final_opponent_reply_policy["bad_reply_rejection_count"] >= 2
    assert second.final_opponent_reply_policy["material_loss_reply_rejection_count"] >= 2
    assert memory_path.exists()
