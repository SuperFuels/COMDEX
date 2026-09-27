from pathlib import Path

import pytest

from backend.modules.aion_inference.int8_dynamic_bank_moe import (
    PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS,
    PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS,
    PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS,
    Int8DynamicBankMoE,
    load_bank_entry,
)
from backend.scripts.run_aion_int8_dynamic_bank_moe_gate import _shader_source


def test_load_bank_entry_rejects_wrong_order() -> None:
    with pytest.raises(RuntimeError, match="ordering"):
        load_bank_entry({"layers": [{"layer": 1}]}, 0, Path("/tmp"), lambda _: "")


def test_load_bank_entry_checks_hash(tmp_path: Path) -> None:
    path = tmp_path / "bank.safetensors"
    path.write_bytes(b"x")
    manifest = {"layers": [{"layer": 0, "path": str(path), "sha256": "ok"}]}
    assert load_bank_entry(manifest, 0, tmp_path.parent, lambda _: "ok")["path"] == str(path)


def test_dynamic_bank_exposes_fused_router_as_opt_in() -> None:
    assert "use_fused_router" in Int8DynamicBankMoE.__init__.__annotations__
    assert "use_fused_prefill_router" in Int8DynamicBankMoE.__init__.__annotations__
    assert "use_fused_projection_pipeline" in Int8DynamicBankMoE.__init__.__annotations__


def test_hybrid_router_freezes_audited_fallback_layers_and_precise_exp() -> None:
    assert PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS == frozenset({19, 21, 22})
    assert PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS == 32
    assert PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS == 8
    source = _shader_source()
    assert "kernel void group_exact_by_expert" in source
    assert "kernel void group_count_exact" in source
    assert "precise::exp" in source[source.index("kernel void select_decode"):]
