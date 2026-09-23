import json,numpy as np,pytest
from backend.modules.hexcore.governed_embodied_experience_router import SCHEMA,VISUAL_DIM,digest,load_runtime,sha256
def fixture(tmp_path):
 states=np.zeros((2,VISUAL_DIM+3),dtype=np.float32);states[1,-3:-1]=.1;actions=np.asarray([[1.,0.],[0.,1.]],dtype=np.float32);archive=tmp_path/'r.npz';np.savez_compressed(archive,states=states,actions=actions,steps=np.asarray([0,0]),protected=np.asarray([True,False]))
 manifest={'schema_version':SCHEMA,'archive_sha256':sha256(archive),'proprio_mean':[0,0],'proprio_scale':[1,1],'proprio_low':[-2,-2],'proprio_high':[2,2],'action_low':[-2,-2],'action_high':[2,2],'phase_window':1,'visual_weight':1.,'proprio_weight':1.,'correction_margin':.5,'maximum_action_disagreement':8.,'ood_radius':12.};manifest['capsule_digest']=digest(manifest);path=tmp_path/'m.json';path.write_text(json.dumps(manifest));return path,archive
def test_protected_experience_is_default_and_integrity_holds(tmp_path):
 m,a=fixture(tmp_path);r=load_runtime(m,a);rgb=np.zeros((96,128,3),dtype=np.uint8);result=r.propose(rgb,np.zeros(2),episode_id=0,step=0);assert result['policy_mode']=='protected_success_experience';assert np.allclose(result['values'],[1,0])
 data=json.loads(m.read_text());data['correction_margin']=9;m.write_text(json.dumps(data))
 with pytest.raises(ValueError,match='integrity'):load_runtime(m,a)
