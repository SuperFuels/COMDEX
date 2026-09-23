from types import SimpleNamespace

from backend.scripts.run_aion_fused_layer_sensitivity_plan import _set_one


def test_set_one_enables_only_selected_layer() -> None:
    layers = [SimpleNamespace(block_sparse_moe=SimpleNamespace(
        experts=SimpleNamespace(use_fused_metal_matvec=False))) for _ in range(2)]
    model = SimpleNamespace(model=SimpleNamespace(layers=layers))
    _set_one(model, 1)
    assert not model.model.layers[0].block_sparse_moe.experts.use_fused_metal_matvec
    assert model.model.layers[1].block_sparse_moe.experts.use_fused_metal_matvec
