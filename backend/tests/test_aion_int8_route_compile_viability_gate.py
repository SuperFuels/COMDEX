from backend.scripts.run_aion_int8_route_compile_viability_gate import (
    _coverage, _route_leaves,
)


def test_route_leaves_normalizes_nested_routes() -> None:
    assert _route_leaves([[[3, 1, 3]], [[2, 4]]]) == [(1, 3), (2, 4)]


def test_coverage_uses_most_common_routes() -> None:
    routes = [(1, 2), (1, 2), (3, 4), (5, 6)]
    assert _coverage(routes, 1) == 0.5
    assert _coverage(routes, 2) == 0.75
