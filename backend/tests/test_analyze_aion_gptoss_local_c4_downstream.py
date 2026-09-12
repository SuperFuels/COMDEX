from __future__ import annotations

import numpy as np
import pytest

from backend.scripts.analyze_aion_gptoss_local_c4_downstream import router_score_consequence


def test_router_consequence_reports_sufficient_set_margin_bound():
    teacher = np.arange(128, dtype=np.float32)
    candidate = teacher.copy()
    candidate[123] += 0.1
    result = router_score_consequence(teacher, candidate)
    assert result['teacher_fourth_fifth_margin'] == 1
    assert result['sufficient_top_four_set_stability_bound']
    candidate[123] = 125
    assert not router_score_consequence(teacher, candidate)['sufficient_top_four_set_stability_bound']


def test_router_consequence_does_not_certify_tied_boundaries():
    teacher = np.arange(128, dtype=np.float32)
    teacher[123] = teacher[124]
    result = router_score_consequence(teacher, teacher)
    assert result['twice_perturbation_over_admission_margin'] is None
    assert not result['sufficient_top_four_set_stability_bound']
    with pytest.raises(ValueError):
        router_score_consequence(np.zeros(127), np.zeros(128))
