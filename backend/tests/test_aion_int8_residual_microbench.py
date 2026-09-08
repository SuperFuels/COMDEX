import torch

from backend.scripts.run_aion_int8_residual_microbench import _residual_shelf


def test_residual_shelf_selects_highest_error_column() -> None:
    weight = torch.tensor([[0.0, 5.0, 0.0, 1.0], [0.0, 5.0, 0.0, 1.0]])
    packed = torch.zeros_like(weight, dtype=torch.int8)
    scale = torch.ones(2)
    indexes, residual = _residual_shelf(weight, packed, scale, 0.24)
    assert indexes.tolist() == [1]
    assert residual.shape == (2, 1)
