"""Teacher-removed v13 nominal controller with v28 temporal recovery."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
from types import SimpleNamespace
from typing import Any,Mapping
import joblib,numpy as np,torch
from backend.modules.hexcore.episodic_embodied_skill_memory import load_runtime
from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.recovery_visual_router import RGBObjectKeypoint

_LOADED=None
def digest(value:Any)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
class Runtime:
 def __init__(self):
  capsule=joblib.load(os.environ['AION_RECOVERY_CAPSULE']);self.capsule=capsule;self.device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');self.keypoint=RGBObjectKeypoint();self.keypoint.load_state_dict(capsule['keypoint_state_dict']);self.keypoint.to(self.device).eval();self.router=capsule['router'];self.threshold=float(capsule['router_threshold']);self.recovery=capsule['recovery_policy'];self.nominal=load_runtime(Path(os.environ['AION_EPISODIC_MANIFEST']),Path(os.environ['AION_EPISODIC_ARCHIVE']),device=self.device);self.episode=None;self.pro=[];self.uv=[];self.actions=[];self.pending=[]
 def reset(self,episode):self.episode=episode;self.pro=[];self.uv=[];self.actions=[];self.pending=[]
 def point(self,rgb):
  with torch.inference_mode():return self.keypoint(torch.from_numpy(np.asarray(rgb,dtype=np.uint8)[None]).to(self.device)).cpu().numpy()[0]
 def temporal(self,base,pro,uv):
  if not self.pro:return np.concatenate((base,np.zeros(18),np.zeros(18),np.zeros(2),np.zeros(2),np.zeros(8),np.zeros(8),np.zeros(8))).astype(np.float32)
  p1=self.pro[-1];p4=self.pro[max(0,len(self.pro)-4)];u1=self.uv[-1];u4=self.uv[max(0,len(self.uv)-4)];a1=self.actions[-1];a4=self.actions[max(0,len(self.actions)-4)];amean=np.mean(self.actions[-4:],axis=0)
  return np.concatenate((base,pro-p1,pro-p4,uv-u1,uv-u4,a1,amean,a1-a4)).astype(np.float32)
 def propose(self,rgb,pro,episode,step):
  if self.episode!=episode or step==0:self.reset(episode)
  pro=np.asarray(pro,np.float32);uv=self.point(rgb);base=make_features(pro[None],uv[None],np.asarray([step]))[0];temporal=self.temporal(base,pro,uv);prob=float(self.router.predict_proba(temporal[None])[0,1]);mode='nominal_v13'
  if self.pending:
   action=np.asarray(self.pending.pop(0),np.float32);mode='recovery_chunk_continuation'
  elif prob>=self.threshold:
   chunk=self.recovery.predict(base[None])[0].reshape(-1,8);action=np.asarray(chunk[0],np.float32);self.pending=[row.copy() for row in chunk[1:]];mode='temporal_recovery_chunk'
  else:
   proposal=self.nominal.propose(np.asarray(rgb,np.uint8),pro,episode_id=episode,step=step);action=np.zeros(8,np.float32) if proposal.get('abstain') else np.asarray(proposal['values'],np.float32);mode=proposal.get('policy_mode','nominal_v13')
  self.pro.append(pro.copy());self.uv.append(uv.copy());self.actions.append(action.copy());return action,mode,prob
def runtime():
 global _LOADED
 if _LOADED is None:_LOADED=Runtime()
 return _LOADED
def propose(*,permitted:Mapping[str,Any],action_space:Any,arm_id:str,**_:Any):
 if arm_id=='aion_cold':values=np.zeros(action_space.shape,np.float32);mode='matched_memory_free_cold_control';prob=0.0
 elif arm_id=='aion_retained':
  r=runtime().nominal.propose(np.asarray(permitted['rgb'],np.uint8),np.asarray(permitted['proprioception_bounded'],np.float32),episode_id=int(permitted['episode_id']),step=int(permitted['timestamp']));values=np.zeros(action_space.shape,np.float32) if r.get('abstain') else np.asarray(r['values'],np.float32);mode='protected_v13';prob=0.0
 elif arm_id=='aion_distilled':values,mode,prob=runtime().propose(np.asarray(permitted['rgb'],np.uint8),np.asarray(permitted['proprioception_bounded'],np.float32),int(permitted['episode_id']),int(permitted['timestamp']))
 else:raise RuntimeError('temporal_recovery_adapter_arm_mismatch')
 values=np.clip(values,np.asarray(action_space.low),np.asarray(action_space.high)).astype(np.float32).reshape(action_space.shape);space=digest({'shape':list(action_space.shape),'low':np.asarray(action_space.low).tolist(),'high':np.asarray(action_space.high).tolist(),'dtype':str(action_space.dtype)})
 return {'values':values,'prediction':{'kind':mode,'policy_mode':mode,'teacher_used':False,'runtime_privileged_inputs':[],'recovery_probability':prob,'abstained':False},'action_space_digest':space}
