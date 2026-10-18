import torch

from backend.scripts.run_aion_int4pack_expert_sweep import (
    _dequantize_int4_groups, _quantize_int4_groups,
)


def test_int4_group_format_round_trips_with_bounded_error() -> None:
    weight = torch.linspace(-2, 3, 128, dtype=torch.float16).reshape(2, 64)
    nibbles, qparams = _quantize_int4_groups(weight, 32)
    restored = _dequantize_int4_groups(nibbles, qparams, 32)
    assert nibbles.dtype == torch.uint8
    assert qparams.dtype == torch.float16
    assert nibbles.shape == (2, 32)
    assert qparams.shape == (2, 2, 2)
    assert float((restored - weight.float()).abs().max()) < 0.18


def test_int4_group_format_rejects_incompatible_width() -> None:
    try:
        _quantize_int4_groups(torch.ones((2, 65), dtype=torch.float16), 32)
    except ValueError:
        return
    raise AssertionError("incompatible width must be rejected")


def test_int4_group_format_rejects_invalid_clip_ratio() -> None:
    try:
        _quantize_int4_groups(torch.ones((2, 64), dtype=torch.float16), 32, 1.1)
    except ValueError:
        return
    raise AssertionError("invalid clipping ratio must be rejected")
