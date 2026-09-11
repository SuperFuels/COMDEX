from backend.scripts.run_aion_gptoss_first_token_gate import (
    overlap_enabled_for_pass,
    parse_layer_spec,
    should_overlap_layer,
)


def test_balanced_pass_pattern_selects_only_candidate_passes():
    assert [overlap_enabled_for_pass(True, "00110", index) for index in range(5)] == [
        False,
        False,
        True,
        True,
        False,
    ]


def test_overlap_is_reserved_for_two_or_more_pending_experts():
    assert not should_overlap_layer(True, 0)
    assert not should_overlap_layer(True, 1)
    assert should_overlap_layer(True, 2)
    assert should_overlap_layer(True, 4)
    assert not should_overlap_layer(False, 4)


def test_adaptive_layer_ranges_are_explicit_and_bounded():
    assert parse_layer_spec("0-3,8,20-21") == {0, 1, 2, 3, 8, 20, 21}
    assert parse_layer_spec(None) == set(range(36))
