from backend.modules.aion_games import run_full_chess_rating_benchmark_kernel


def test_phase22b26_runs_rating_benchmark(tmp_path):
    result = run_full_chess_rating_benchmark_kernel(
        memory_path=tmp_path / "rating_benchmark_memory.json"
    )

    assert result.kernel_version == "phase22b26_full_chess_rating_benchmark_kernel_v1"
    assert result.board_size == 8
    assert result.benchmark_match_count == 4
    assert result.completed_match_count == 4
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase22b26_records_benchmark_outcomes(tmp_path):
    result = run_full_chess_rating_benchmark_kernel(
        memory_path=tmp_path / "rating_benchmark_memory.json"
    )

    assert result.win_count == 2
    assert result.draw_count == 1
    assert result.loss_count == 1
    assert result.score_total == 2.5
    assert result.score_percentage == 62.5
    assert result.evidence["records_wins"] is True
    assert result.evidence["records_draws"] is True
    assert result.evidence["records_losses"] is True


def test_phase22b26_derives_rating_band(tmp_path):
    result = run_full_chess_rating_benchmark_kernel(
        memory_path=tmp_path / "rating_benchmark_memory.json"
    )

    assert result.lowest_opponent_rating == 400
    assert result.highest_opponent_rating == 1000
    assert result.estimated_rating_floor == 700
    assert result.estimated_rating_ceiling == 850
    assert result.estimated_rating_band_label == "early tactical scaffold"
    assert result.benchmark_passed is True


def test_phase22b26_emits_benchmark_trace_hash(tmp_path):
    result = run_full_chess_rating_benchmark_kernel(
        memory_path=tmp_path / "rating_benchmark_memory.json"
    )

    assert len(result.rating_benchmark_trace_hash) == 64
    assert result.evidence["uses_trace_hash"] is True


def test_phase22b26_persists_rating_benchmark_memory(tmp_path):
    memory_path = tmp_path / "rating_benchmark_memory.json"

    first = run_full_chess_rating_benchmark_kernel(memory_path=memory_path)
    second = run_full_chess_rating_benchmark_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_rating_benchmark_policy["kernel_run_count"] >= 2
    assert second.final_rating_benchmark_policy["rating_benchmark_count"] >= 2
    assert second.final_rating_benchmark_policy["benchmark_match_total"] >= 8
    assert second.final_rating_benchmark_policy["benchmark_score_total"] >= 5.0
    assert memory_path.exists()
