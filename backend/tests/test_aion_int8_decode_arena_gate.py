from backend.scripts.run_aion_int8_decode_arena_gate import _summary


def test_decode_arena_summary_has_nearest_rank_tail() -> None:
    result = _summary([1.0, 2.0, 3.0, 4.0])
    assert result["p50_seconds"] == 2.5
    assert result["p95_seconds_nearest_rank"] == 4.0
