from backend.scripts.analyze_aion_gptoss_exact_reuse_frontier import (
    retention_frontier,
    weighted_reuse_distances,
)


def test_weighted_reuse_distance_counts_unique_intervening_bytes():
    sizes = {"a": 10, "b": 20, "c": 30}
    assert weighted_reuse_distances(["a", "b", "a", "c", "b"], sizes) == [20, 40]


def test_retention_frontier_accounts_first_touch_floor():
    sizes = {"a": 10, "b": 20}
    result = retention_frontier(["a", "b", "a", "a"], sizes)
    assert result["total_delivery_bytes"] == 50
    assert result["first_touch_floor_bytes"] == 30
    assert result["maximum_avoidable_repeat_bytes"] == 20
    assert result["maximum_avoidable_fraction"] == 0.4
    assert result["minimum_capacity_for_total_delivery_reduction"]["0.5"] is None
