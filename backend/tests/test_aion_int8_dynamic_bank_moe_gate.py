from backend.scripts.run_aion_int8_dynamic_bank_moe_gate import _shader_source, _summary


def test_dynamic_bank_shader_keeps_indices_on_device() -> None:
    source = _shader_source()
    assert "device const int* experts" in source
    assert "simd_sum" in source
    assert "tolist" not in source


def test_dynamic_bank_summary_reports_tail() -> None:
    result = _summary([1.0, 2.0, 3.0])
    assert result["p50_seconds"] == 2.0
    assert result["p95_seconds_nearest_rank"] == 3.0
