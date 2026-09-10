import numpy as np

from backend.scripts.run_aion_gptoss_exact_expert_batch_gate import deterministic_inputs


def test_deterministic_batch_inputs_are_distinct_and_repeatable() -> None:
    first = deterministic_inputs(4)
    second = deterministic_inputs(4)
    assert all(np.array_equal(left, right) for left, right in zip(first, second))
    assert first[0].shape == (4, 2880)
    assert first[1].shape == (4, 2880)
    assert first[2].shape == (4,)
    assert not np.array_equal(first[0][0], first[0][1])
