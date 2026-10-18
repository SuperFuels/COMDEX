from backend.scripts.run_aion_int8_fused_metal_matvec_gate import _shader_source


def test_fused_shader_has_eight_weight_scale_pairs_and_simd_reduction() -> None:
    source = _shader_source()
    for index in range(8):
        assert f"w{index}" in source
        assert f"s{index}" in source
    assert "simd_sum" in source
    assert "column += 32" in source
