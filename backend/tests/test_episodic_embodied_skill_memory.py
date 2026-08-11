import json
import numpy as np
import pytest
from backend.modules.hexcore.episodic_embodied_skill_memory import SCHEMA, digest, load_runtime, sha256, spatial_state

def make(tmp_path):
    mean=np.zeros(4,dtype=np.float32); scale=np.ones(4,dtype=np.float32)
    rgb=np.zeros((96,128,3),dtype=np.uint8)
    state=spatial_state(rgb,rgb,np.zeros(4),0,proprio_mean=mean,proprio_scale=scale)
    archive=tmp_path/'skill.npz'; np.savez_compressed(archive,states=np.stack([state]),actions=np.ones((1,2),dtype=np.float32),steps=np.asarray([0],dtype=np.int16))
    manifest={"schema_version":SCHEMA,"archive_sha256":sha256(archive),"proprio_mean":mean.tolist(),
      "proprio_scale":scale.tolist(),"proprio_low":[-2]*4,"proprio_high":[2]*4,
      "action_low":[-2]*2,"action_high":[2]*2,"neighbour_count":1,
      "retrieval_temperature":.05,"phase_window":1,"ood_radius":5.0}
    manifest['capsule_digest']=digest(manifest); path=tmp_path/'manifest.json'; path.write_text(json.dumps(manifest))
    return path,archive,rgb
def test_exact_experience_reconstruction(tmp_path):
    manifest,archive,rgb=make(tmp_path); runtime=load_runtime(manifest,archive)
    result=runtime.propose(rgb,np.zeros(4),episode_id=0,step=0)
    assert result['abstain'] is False and np.allclose(result['values'],1)
def test_integrity_and_ood_fail_closed(tmp_path):
    manifest,archive,rgb=make(tmp_path); data=json.loads(manifest.read_text()); data['ood_radius']=9; manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='integrity'): load_runtime(manifest,archive)
    manifest,archive,rgb=make(tmp_path); runtime=load_runtime(manifest,archive)
    assert runtime.propose(rgb,np.full(4,20),episode_id=0,step=0)['abstain'] is True
