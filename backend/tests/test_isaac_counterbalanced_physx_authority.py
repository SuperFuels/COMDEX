from integrations.isaac_lab.run_counterbalanced_physx_authority import summarize, wilson


def rows(arm: str, successes: tuple[int, int]):
    result = []
    for repeat, count in enumerate(successes):
        for episode in range(6):
            result.append({
                "arm_id": arm, "process_repeat": repeat, "success": episode < count,
                "unsafe": False, "return": float(episode < count),
                "max_object_height_m": .11 if episode < count else .055,
            })
    return result


def test_wilson_is_bounded() -> None:
    low, high = wilson(6, 12)
    assert 0.0 < low < .5 < high < 1.0


def test_counterbalanced_gate_requires_both_processes_and_positive_confidence() -> None:
    weak = summarize(rows("aion_retained", (1, 1)) + rows("aion_distilled", (2, 2)))
    assert weak["development_gate_passed"]
    assert weak["process_level_direction_consistent"]
    assert not weak["sealed_tournament_authorized"]
    strong = summarize(rows("aion_retained", (0, 0)) + rows("aion_distilled", (6, 6)))
    assert strong["sealed_tournament_authorized"]


def test_counterbalanced_gate_rejects_one_process_regression() -> None:
    result = summarize(rows("aion_retained", (0, 2)) + rows("aion_distilled", (4, 1)))
    assert result["development_gate_passed"]
    assert not result["process_level_direction_consistent"]
    assert not result["sealed_tournament_authorized"]
