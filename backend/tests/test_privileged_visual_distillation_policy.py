import json
from pathlib import Path
import numpy as np
import pytest
import torch
from backend.modules.hexcore.privileged_visual_distillation_policy import SCHEMA,PrivilegedVisualPolicy,digest,load_runtime,sha256

def capsule(tmp_path:Path):
    model=PrivilegedVisualPolicy(); weights=tmp_path/"w.pt"; torch.save(model.state_dict(),weights)
    manifest={"schema_version":SCHEMA,"weights_sha256":sha256(weights),"proprio_dim":18,"action_dim":8,"label_dim":10,"hidden_dim":256,"action_mean":[0]*8,"action_scale":[1]*8,"action_low":[-1]*8,"action_high":[1]*8,"proprio_low":[-2]*18,"proprio_high":[2]*18,"runtime_privileged_inputs":[]}
    manifest["capsule_digest"]=digest(manifest); path=tmp_path/"m.json"; path.write_text(json.dumps(manifest)); return path,weights
def test_runtime_uses_no_privileged_channel(tmp_path):
    m,w=capsule(tmp_path); runtime=load_runtime(m,w); result=runtime.propose(np.zeros((96,128,3),np.uint8),np.zeros(18,np.float32),episode_id=1,step=0)
    assert not result["abstain"] and len(result["belief"])==10 and not result["teacher_used"]
def test_integrity_and_privilege_fail_closed(tmp_path):
    m,w=capsule(tmp_path); data=json.loads(m.read_text()); data["runtime_privileged_inputs"]=["goal_pose"]; data["capsule_digest"]=digest({k:v for k,v in data.items() if k!="capsule_digest"}); m.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="privileged_runtime_channel_forbidden"): load_runtime(m,w)
def test_ood_abstention_and_episode_reset(tmp_path):
    m,w=capsule(tmp_path); runtime=load_runtime(m,w); image=np.zeros((96,128,3),np.uint8)
    assert runtime.propose(image,np.full(18,3,np.float32),episode_id=1,step=0)["abstain"]
    first=runtime.propose(image,np.zeros(18,np.float32),episode_id=2,step=0)["values"]
    again=runtime.propose(image,np.zeros(18,np.float32),episode_id=3,step=0)["values"]
    np.testing.assert_allclose(first,again)

def test_weights_tamper_fails_closed(tmp_path):
    m,w=capsule(tmp_path); w.write_bytes(w.read_bytes()+b"tamper")
    with pytest.raises(ValueError,match="weights_integrity_failure"): load_runtime(m,w)
