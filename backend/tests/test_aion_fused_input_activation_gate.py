from backend.scripts.run_aion_int8_dynamic_bank_moe_gate import _shader_source


def test_fused_input_silu_preserves_half_staging() -> None:
    source = _shader_source()
    fused = source[source.index("kernel void dyn_input_silu"):]
    assert "half gate_h" in fused
    assert "half projected_h" in fused
    assert "half silu_h" in fused
    assert "fast::exp" in fused
    assert "kernel void dyn_output_parallel4" in source
    assert "kernel void dyn_input_silu2" in source
    assert "threadgroup half staged[2]" in source
    router = source[source.index("kernel void select_decode"):]
    assert "precise::exp" in router
