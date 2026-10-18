from backend.scripts.analyze_aion_gptoss_route_slab_reuse import (
    extract_run_routes,
    summarize,
)


def test_three_touch_slab_counts_only_later_reuse() -> None:
    route = (12, (1, 2, 3, 4))
    other = (12, (5, 6, 7, 8))
    result = summarize([route] * 5 + [other] * 3, touches=3, slab_bytes=100)
    assert result["route_occurrences"] == 8
    assert result["unique_ordered_layer_routes"] == 2
    assert result["admitted_route_slabs"] == 1
    assert result["post_admission_reuses"] == 2
    assert result["post_admission_reuse_fraction"] == 0.25
    assert result["projected_route_slab_storage_bytes"] == 100


def test_route_order_and_layer_are_part_of_identity() -> None:
    result = summarize([
        (0, (1, 2, 3, 4)),
        (0, (4, 3, 2, 1)),
        (1, (1, 2, 3, 4)),
    ], touches=1, slab_bytes=100)
    assert result["unique_ordered_layer_routes"] == 3
    assert result["post_admission_reuses"] == 0


def test_route_prefix_can_measure_pair_reuse() -> None:
    report = {
        "run_a": {
            "tokens": [{
                "layers": [
                    {"layer": 2, "route": [7, 8, 9, 10]},
                    {"layer": 3, "route": [7, 8, 11, 12]},
                ]
            }]
        }
    }
    assert extract_run_routes(report, "run_a", 2) == [
        (2, (7, 8)),
        (3, (7, 8)),
    ]
