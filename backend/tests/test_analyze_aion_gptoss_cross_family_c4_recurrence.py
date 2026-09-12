import numpy as np

from backend.scripts.analyze_aion_gptoss_cross_family_c4_recurrence import (
    percentile,
    unit,
)


def test_unit_normalizes_each_activation() -> None:
    values = np.asarray([[3.0, 4.0], [0.0, 2.0]])
    normalized = unit(values)
    np.testing.assert_allclose(np.linalg.norm(normalized, axis=1), [1.0, 1.0])


def test_percentile_handles_empty_and_nonempty_samples() -> None:
    assert percentile([], 95) is None
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0
