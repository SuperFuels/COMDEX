from backend.modules.aion_games import run_mini_chess_capture_material_learning_kernel


def test_phase22b3_selects_safe_capture_and_rejects_poisoned_material(tmp_path):
    result = run_mini_chess_capture_material_learning_kernel(memory_path=tmp_path / "capture_memory.json")

    assert result.kernel_version == "phase22b3_mini_chess_capture_material_learning_kernel_v1"
    assert result.selected_capture["candidate_id"] == "CAP-1"
    assert result.selected_capture["safe_capture"] is True
    assert result.learned_safe_capture is True
    assert result.avoided_bad_capture is True
    assert result.protected_high_value_piece is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b3_scores_material_gain_against_recapture_risk(tmp_path):
    result = run_mini_chess_capture_material_learning_kernel(memory_path=tmp_path / "capture_memory.json")

    candidates = {c["candidate_id"]: c for c in result.capture_candidates}

    assert candidates["CAP-2"]["immediate_material_gain"] > 0
    assert candidates["CAP-2"]["expected_net_gain"] < 0
    assert candidates["CAP-3"]["attacker_value"] == 9
    assert candidates["CAP-3"]["expected_net_gain"] < 0
    assert result.material_score_delta > 0


def test_phase22b3_persists_capture_learning_memory(tmp_path):
    memory_path = tmp_path / "capture_memory.json"

    first = run_mini_chess_capture_material_learning_kernel(memory_path=memory_path)
    second = run_mini_chess_capture_material_learning_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_capture_policy["kernel_run_count"] >= 2
    assert second.final_capture_policy["safe_capture_learning_count"] >= 2
    assert second.final_capture_policy["bad_capture_avoidance_count"] >= 2
    assert second.final_capture_policy["known_piece_values"]["queen"] == 9
    assert memory_path.exists()
