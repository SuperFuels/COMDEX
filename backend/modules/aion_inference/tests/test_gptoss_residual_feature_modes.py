import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = (Path(__file__).parents[3] / "scripts" /
          "train_aion_top1_residual_mlp.py")
SPEC = importlib.util.spec_from_file_location("aion_residual_mlp", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_full_features_preserve_all_activation_coordinates():
    rows = [{"layer": 7, "route": [3, 8, 14, 21],
             "gates": [0.4, 0.3, 0.2, 0.1]}]
    arrays = {
        "ffn": np.ones((1, MODULE.WIDTH), dtype=np.float32),
        "router": np.full((1, MODULE.WIDTH), 2, dtype=np.float32),
        "top1": np.full((1, MODULE.WIDTH), 3, dtype=np.float32),
    }
    compact = MODULE.features(arrays, rows, "signed_bins")
    full = MODULE.features(arrays, rows, "full")
    fixed_tail = MODULE.LAYERS * MODULE.EXPERTS + MODULE.LAYERS + 6
    assert compact.shape == (1, 3 * MODULE.BINS + fixed_tail)
    assert full.shape == (1, 3 * MODULE.WIDTH + fixed_tail)
    np.testing.assert_array_equal(full[0, :MODULE.WIDTH], arrays["ffn"][0])
    np.testing.assert_array_equal(
        full[0, MODULE.WIDTH:2 * MODULE.WIDTH], arrays["router"][0])


def test_route_and_layer_conditioning_survive_both_modes():
    rows = [{"layer": 2, "route": [1, 4, 9, 16],
             "gates": [0.5, 0.25, 0.15, 0.1]}]
    arrays = {name: np.zeros((1, MODULE.WIDTH), dtype=np.float32)
              for name in ("ffn", "router", "top1")}
    for mode in ("signed_bins", "full"):
        value = MODULE.features(arrays, rows, mode)[0]
        activation_width = 3 * (MODULE.BINS if mode == "signed_bins" else MODULE.WIDTH)
        route = value[activation_width:activation_width + MODULE.LAYERS * MODULE.EXPERTS]
        layer = value[activation_width + MODULE.LAYERS * MODULE.EXPERTS:
                      activation_width + MODULE.LAYERS * MODULE.EXPERTS + MODULE.LAYERS]
        assert route[2 * MODULE.EXPERTS + 1] == np.float32(0.5)
        assert route[2 * MODULE.EXPERTS + 16] == np.float32(0.1)
        assert layer[2] == np.float32(1.0)
