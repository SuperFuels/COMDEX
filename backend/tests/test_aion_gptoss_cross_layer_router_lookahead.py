import numpy as np

from backend.scripts.analyze_aion_gptoss_cross_layer_router_lookahead import (
    canonical_sha,
    rms_norm,
    topk,
)


def test_topk_is_descending_and_stable_for_ties():
    values = np.asarray([1.0, 4.0, 4.0, 2.0], dtype=np.float32)
    assert topk(values, 3) == [2, 1, 3]


def test_rms_norm_uses_float32_and_weight():
    values = np.asarray([3.0, 4.0], dtype=np.float32)
    weight = np.asarray([2.0, 0.5], dtype=np.float32)
    result = rms_norm(values, weight)
    expected_scale = np.float32(1.0 / np.sqrt(np.float32(12.5) + np.float32(1.0e-5)))
    np.testing.assert_array_equal(result, values * expected_scale * weight)
    assert result.dtype == np.float32


def test_canonical_hash_is_order_independent():
    assert canonical_sha({"a": 1, "b": 2}) == canonical_sha({"b": 2, "a": 1})
