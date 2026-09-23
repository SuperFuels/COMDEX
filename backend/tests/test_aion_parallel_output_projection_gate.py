from backend.scripts.run_aion_int8_dynamic_bank_moe_gate import _shader_source
from backend.scripts.run_aion_parallel_output_projection_gate import _summary


def test_parallel_output_kernel_retains_ordered_final_sum() -> None:
    source = _shader_source()
    parallel = source[source.index("kernel void dyn_output_parallel"):]
    assert "threadgroup float contributions[8]" in parallel
    assert "for(uint j=0;j<8;j++)total+=contributions[j]" in parallel
    assert _summary([0.004, 0.001, 0.003, 0.002])["p50_seconds"] == 0.0025
