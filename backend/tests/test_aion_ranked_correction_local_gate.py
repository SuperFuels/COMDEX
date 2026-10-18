import numpy as np
import pytest
from backend.scripts.run_aion_ranked_correction_local_gate import fit_local,predict
from backend.scripts.run_aion_ranked_correction_local_gate import chronological_sanity
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical
import json


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


def test_chronological_smoke_does_not_fit_on_continuation(tmp_path,monkeypatch):
    corpus={'rows':[]};corpus['canonical_sha256']=canonical(corpus)
    path=tmp_path/'corpus.json';path.write_text(json.dumps(corpus))
    data=[{'position':i,'rank':4,'expert':3,'x':np.ones(12,dtype=np.float32)*(1 if i<4 else -1),
           'target':np.ones(12,dtype=np.float32)*.1,'gate':.1,'output_norm':10.} for i in range(5)]
    monkeypatch.setattr('backend.scripts.run_aion_ranked_correction_local_gate.load_job',
                        lambda *args,**kwargs:({'prompt_token_count':4},{'canonical_sha256':'test'},data))
    report=chronological_sanity(tmp_path,path,tmp_path/'output',12)
    assert report['status']=='SANITY_ONLY_NOT_CERTIFIED'
    assert report['results'][0]['fitting_positions']==[0,1,2,3]
    assert report['results'][0]['observations'][0]['position']==4
    assert not report['results'][0]['observations'][0]['supported']
