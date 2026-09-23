import torch

from backend.scripts.run_aion_int8pack_expert_microbench import _quantize_rows


def test_quantize_rows_has_expected_contract() -> None:
    weight = torch.tensor([[0.0, 1.0, -1.0], [2.0, -4.0, 1.0]], dtype=torch.float16)
    packed, scales = _quantize_rows(weight)
    assert packed.dtype == torch.int8
    assert scales.dtype == torch.float16
    assert packed.shape == weight.shape
    assert scales.shape == (2,)
    restored = packed.float() * scales.float()[:, None]
    assert float((restored - weight.float()).abs().max()) < 0.02


def test_quantize_rows_handles_zero_row() -> None:
    packed, scales = _quantize_rows(torch.zeros((2, 4), dtype=torch.float16))
    assert torch.equal(packed, torch.zeros_like(packed))
    assert bool(torch.isfinite(scales).all())
