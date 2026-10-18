from backend.scripts.run_aion_gptoss_first_token_gate import (
    overlap_enabled_for_pass,
    parse_layer_spec,
    should_overlap_layer,
)
from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssPersistentL2ExpertFrameStore,
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


def test_two_touch_l2_admission_protects_cartridge_and_promotes_reuse():
    store = object.__new__(GptOssPersistentL2ExpertFrameStore)
    store._l2_two_touch_admission = True
    store._l2_protected = {(0, 1)}
    store._l2_admission_touches = 2
    store._l2_probation = {}
    store.l2_admission_bypasses = 0
    store.l2_admission_promotions = 0

    assert store._should_admit_l2((0, 1))
    assert not store._should_admit_l2((0, 2))
    assert store._should_admit_l2((0, 2))
    assert store.l2_admission_bypasses == 1
    assert store.l2_admission_promotions == 1
    assert not store._l2_probation


def test_three_touch_l2_admission_rejects_low_frequency_exceptions():
    store = object.__new__(GptOssPersistentL2ExpertFrameStore)
    store._l2_two_touch_admission = True
    store._l2_admission_touches = 3
    store._l2_protected = set()
    store._l2_probation = {}
    store.l2_admission_bypasses = 0
    store.l2_admission_promotions = 0

    assert not store._should_admit_l2((4, 9))
    assert not store._should_admit_l2((4, 9))
    assert store._should_admit_l2((4, 9))
    assert store.l2_admission_bypasses == 2
    assert store.l2_admission_promotions == 1


def test_four_touch_l2_admission_requires_four_exact_demands():
    store = object.__new__(GptOssPersistentL2ExpertFrameStore)
    store._l2_two_touch_admission = True
    store._l2_admission_touches = 4
    store._l2_protected = set()
    store._l2_probation = {}
    store.l2_admission_bypasses = 0
    store.l2_admission_promotions = 0

    assert not store._should_admit_l2((7, 11))
    assert not store._should_admit_l2((7, 11))
    assert not store._should_admit_l2((7, 11))
    assert store._should_admit_l2((7, 11))
    assert store.l2_admission_bypasses == 3
    assert store.l2_admission_promotions == 1
