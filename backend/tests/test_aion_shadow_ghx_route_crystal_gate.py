from __future__ import annotations

import numpy as np

from backend.modules.aion_inference.ghx_route_crystal import GhxRouteCrystalSelector
from backend.scripts.run_aion_shadow_ghx_route_crystal_gate import (
    ROUTE_WEIGHT,
    kernel,
    relative_l2,
    route_vector,
)


def test_route_vector_preserves_expert_identity_and_gate() -> None:
    value = route_vector({"route": [7, 3, 99, 12], "gates": [.4, .3, .2, .1]})
    assert value.shape == (128,)
    assert np.count_nonzero(value) == 4
    assert value[7] == .4
    assert value[99] == .2


def test_kernel_rewards_matching_route_crystal() -> None:
    router = np.asarray([[1.0, 0.0]])
    matching = np.zeros((1, 128)); matching[0, 7] = 1.0
    different = np.zeros((1, 128)); different[0, 8] = 1.0
    same = kernel(router, matching, router, matching)[0, 0]
    other = kernel(router, matching, router, different)[0, 0]
    assert same - other == ROUTE_WEIGHT


def test_relative_l2_is_zero_for_identical_values() -> None:
    value = np.asarray([1.0, -2.0, 3.0])
    assert relative_l2(value, value) == 0.0


def test_selector_retains_fast_matching_without_authorizing_substitution() -> None:
    routers = np.zeros((2, 2880), dtype=np.float32)
    routers[0, 0] = 1
    routers[1, 1] = 1
    routes = np.zeros((2, 128), dtype=np.float32)
    routes[0, 7] = 1
    routes[1, 8] = 1
    selector = GhxRouteCrystalSelector(routers, routes, route_weight=16)
    router = np.zeros(2880, dtype=np.float32); router[0] = 1
    selected = selector.select(router, [7], [1.0], top_k=2)
    assert selected.prototype_indices == (0, 1)
    assert selected.score_margin > 0
    assert selected.observed_expert_fraction == 1.0
