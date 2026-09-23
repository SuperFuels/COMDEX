import torch

from backend.scripts.run_aion_activation_aware_int4_gate import _choose_clip


def test_choose_clip_returns_one_declared_candidate() -> None:
    weight = torch.randn((4, 64), generator=torch.Generator().manual_seed(7)).half()
    weight[0, 0] = 20
    nibbles, qparams, ratio, losses = _choose_clip(
        weight, torch.ones(64), 32, (1.0, 0.95, 0.85),
    )
    assert ratio in (1.0, 0.95, 0.85)
    assert len(losses) == 3
    assert nibbles.shape == (4, 32)
    assert qparams.shape == (2, 4, 2)
