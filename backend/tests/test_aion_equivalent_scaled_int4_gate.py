import torch

from backend.scripts.run_aion_equivalent_scaled_int4_gate import (
    _choose_alpha, _equivalent_scale,
)


def test_equivalent_scale_is_bounded_and_group_normalized() -> None:
    weight = torch.randn((8, 64), generator=torch.Generator().manual_seed(12)).half()
    energy = torch.linspace(0.1, 4, 64)
    scale = _equivalent_scale(weight, energy, 0.5, 32)
    assert scale.shape == (64,)
    assert float(scale.min()) >= 0.25
    assert float(scale.max()) <= 4.0


def test_choose_alpha_includes_identity_control() -> None:
    weight = torch.randn((4, 64), generator=torch.Generator().manual_seed(13)).half()
    result = _choose_alpha(weight, torch.ones(64), (0.25, 0.5), 32)
    assert result[3] in {"identity", "0.25", "0.5"}
    assert set(result[4]) == {"identity", "0.25", "0.5"}
