from backend.modules.aion_games import run_full_chess_learning_loop_kernel


def test_phase22b16_generates_learning_signals(tmp_path):
    result = run_full_chess_learning_loop_kernel(memory_path=tmp_path / "learning_memory.json")

    assert result.kernel_version == "phase22b16_full_chess_learning_loop_kernel_v1"
    assert result.board_size == 8
    assert result.learning_signal_count >= 6
    assert result.positive_learning_count >= 3
    assert result.negative_learning_count >= 3
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b16_reinforces_good_chess_lines(tmp_path):
    result = run_full_chess_learning_loop_kernel(memory_path=tmp_path / "learning_memory.json")

    assert result.reinforced_safe_capture_count >= 1
    assert result.reinforced_surviving_strategy_count >= 1
    assert result.reinforced_multi_ply_line_count >= 1
    assert result.evidence["reinforces_safe_capture"] is True
    assert result.evidence["reinforces_surviving_strategy"] is True
    assert result.evidence["reinforces_multi_ply_line"] is True


def test_phase22b16_weakens_bad_chess_lines(tmp_path):
    result = run_full_chess_learning_loop_kernel(memory_path=tmp_path / "learning_memory.json")

    assert result.weakened_greedy_capture_count >= 1
    assert result.weakened_king_exposure_count >= 1
    assert result.weakened_material_loss_count >= 1
    assert result.evidence["weakens_greedy_capture"] is True
    assert result.evidence["weakens_king_exposure"] is True
    assert result.evidence["weakens_material_loss"] is True


def test_phase22b16_outputs_learned_policy(tmp_path):
    result = run_full_chess_learning_loop_kernel(memory_path=tmp_path / "learning_memory.json")

    assert result.learned_policy["prefer_safe_profitable_capture"] is True
    assert result.learned_policy["prefer_multi_ply_surviving_line"] is True
    assert result.learned_policy["avoid_greedy_bad_capture"] is True
    assert result.learned_policy["avoid_king_exposure_line"] is True
    assert result.preferred_strategy_after_learning == "STRAT-1 / LINE-1"
    assert result.avoided_strategy_after_learning == "STRAT-2 greedy queen capture"
    assert len(result.learning_loop_trace_hash) == 64


def test_phase22b16_persists_learning_memory(tmp_path):
    memory_path = tmp_path / "learning_memory.json"

    first = run_full_chess_learning_loop_kernel(memory_path=memory_path)
    second = run_full_chess_learning_loop_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_learning_policy["kernel_run_count"] >= 2
    assert second.final_learning_policy["learning_loop_count"] >= 2
    assert second.final_learning_policy["safe_capture_weight"] > first.final_learning_policy["safe_capture_weight"]
    assert second.final_learning_policy["greedy_capture_penalty"] > first.final_learning_policy["greedy_capture_penalty"]
    assert memory_path.exists()
