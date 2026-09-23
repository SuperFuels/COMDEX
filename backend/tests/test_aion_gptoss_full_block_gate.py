from backend.scripts.run_aion_gptoss_full_block_gate import union_schedule


def test_union_schedule_is_sorted_and_deduplicated():
    routes = [[9, 2, 7, 1], [7, 3, 9, 5]]
    assert union_schedule(routes) == [1, 2, 3, 5, 7, 9]


def test_union_schedule_retains_disjoint_routes():
    routes = [[0, 1, 2, 3], [4, 5, 6, 7]]
    assert union_schedule(routes) == list(range(8))


def test_two_position_union_fits_one_eight_worker_wave():
    routes = [[0, 1, 2, 3], [2, 4, 5, 6]]
    assert len(union_schedule(routes)) <= 8
