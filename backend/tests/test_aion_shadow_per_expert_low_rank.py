from __future__ import annotations

import numpy as np

from backend.scripts.train_aion_shadow_per_expert_low_rank import expert_kernel, route


def test_route_is_sparse_and_gate_bound() -> None:
    value = route({"route": [1, 7, 19, 127], "gates": [.4, .3, .2, .1]})
    assert value.shape == (128,)
    assert np.count_nonzero(value) == 4
    assert value[19] == .2


def test_per_expert_kernel_separates_disjoint_routes() -> None:
    activation = np.asarray([[1.0, 0.0]])
    first = np.zeros((1, 128)); first[0, 4] = 1
    second = np.zeros((1, 128)); second[0, 5] = 1
    same = expert_kernel(activation, first, activation, first, 0)[0, 0]
    disjoint = expert_kernel(activation, first, activation, second, 0)[0, 0]
    assert same > disjoint
    assert disjoint == 0
