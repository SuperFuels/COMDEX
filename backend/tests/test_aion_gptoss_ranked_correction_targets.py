import numpy as np
import pytest

from backend.scripts.run_aion_gptoss_first_token_gate import ranked_correction_target_blobs, WIDTH


def test_targets_retain_rank_and_original_f32_values():
    contributions=[np.full(WIDTH,i+.125,dtype=np.float32).astype(np.float64) for i in range(4)]
    blobs=ranked_correction_target_blobs(contributions)
    assert set(blobs)=={'second_contribution','third_contribution','fourth_contribution'}
    for slot,name in enumerate(('second_contribution','third_contribution','fourth_contribution'),1):
        assert len(blobs[name])==11520
        assert blobs[name]==contributions[slot].astype('<f4').tobytes()


def test_reduced_calls_only_emit_available_targets():
    assert set(ranked_correction_target_blobs([np.zeros(WIDTH)]*2))=={'second_contribution'}
    assert ranked_correction_target_blobs([np.zeros(WIDTH)])=={}


def test_bad_target_cannot_be_saved():
    with pytest.raises(ValueError,match='2880 finite'):
        ranked_correction_target_blobs([np.zeros(WIDTH),np.full(WIDTH,np.nan)])
