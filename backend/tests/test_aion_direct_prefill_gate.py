from backend.scripts.run_aion_int8_dynamic_bank_moe_gate import _shader_source


def test_direct_prefill_kernels_keep_token_major_routes_on_device() -> None:
    source = _shader_source()
    assert "kernel void prefill_input_silu" in source
    assert "token=assignment/8" in source
    assert "kernel void prefill_output" in source
    assert "uint assignment=token*8+slot" in source
