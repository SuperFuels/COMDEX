import numpy as np
import pytest
from backend.scripts.run_aion_ranked_correction_local_gate import fit_local,predict


def test_affine_target_transfer_is_not_a_stored_answer():
    rng=np.random.default_rng(11)
    base=np.ones(12)*5
    direction=np.arange(12)/12
    x=np.asarray([base+i*direction for i in (0,.2,.4,.6)])
    gates=np.asarray([.1,.2,.3,.4])
    y=(x*.7+2)*gates[:,None]
    model=fit_local(x,y,gates)
    unseen=base+.3*direction
    prediction,similarity=predict(model,unseen.astype(np.float32),.25)
    assert similarity>=.80
    assert np.linalg.norm(prediction-(unseen*.7+2)*.25)<.01


def test_outside_activation_support_falls_back():
    x=np.ones((4,12));y=x*.1
    model=fit_local(x,y,[.1]*4)
    assert predict(model,-np.ones(12,dtype=np.float32),.1)[0] is None


def test_tiny_training_support_is_rejected():
    with pytest.raises(ValueError,match='four aligned'):
        fit_local(np.ones((2,12)),np.ones((2,12)),[.1,.1])
