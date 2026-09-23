from collections import defaultdict


def test_occurrence_groups_preserve_position_and_slot() -> None:
    routes = [[7, 2, 9, 1], [9, 3, 7, 4]]
    groups = defaultdict(list)
    for position, route in enumerate(routes):
        for slot, expert in enumerate(route):
            groups[expert].append((position, slot))
    assert groups[7] == [(0, 0), (1, 2)]
    assert groups[9] == [(0, 2), (1, 0)]
    assert groups[2] == [(0, 1)]
