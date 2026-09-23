from backend.scripts.run_aion_exact_prefix_kv_abba import _longest_common_prefix


def test_longest_common_prefix_is_token_exact() -> None:
    assert _longest_common_prefix([[1, 2, 3, 4], [1, 2, 8], [1, 2, 3]]) == [1, 2]


def test_longest_common_prefix_handles_empty_input() -> None:
    assert _longest_common_prefix([]) == []
    assert _longest_common_prefix([[1], []]) == []


def test_longest_common_prefix_can_cover_shortest_sequence() -> None:
    assert _longest_common_prefix([[4, 5], [4, 5, 6]]) == [4, 5]
