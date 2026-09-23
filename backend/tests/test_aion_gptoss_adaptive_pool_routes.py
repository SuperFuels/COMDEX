from __future__ import annotations

import pytest

from backend.scripts.build_aion_gptoss_adaptive_expert_pool import (
    extract_reduced_routes,
)


def _report(route: list[int]) -> dict:
    return {
        "run_b": {
            "tokens": [{
                "layers": [
                    {"layer": layer, "route": route}
                    for layer in range(36)
                ]
            }]
        }
    }


@pytest.mark.parametrize("active", [1, 2, 3, 4])
def test_reduced_route_evidence_accepts_one_to_four_unique_experts(active: int) -> None:
    routes = extract_reduced_routes(_report(list(range(active))))
    assert len(routes) == 1
    assert len(routes[0]) == 36
    assert routes[0][0] == list(range(active))


@pytest.mark.parametrize("route", [[], [1, 1], [128], [0, 1, 2, 3, 4]])
def test_reduced_route_evidence_rejects_invalid_routes(route: list[int]) -> None:
    with pytest.raises(ValueError):
        extract_reduced_routes(_report(route))


def test_reduced_route_evidence_requires_all_layers() -> None:
    report = _report([1, 2])
    report["run_b"]["tokens"][0]["layers"].pop()
    with pytest.raises(ValueError):
        extract_reduced_routes(report)
