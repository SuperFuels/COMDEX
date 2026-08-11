from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import numpy as np,torch
from backend.modules.hexcore.geometry_routed_program_memory import load_runtime
_R=None
def dg(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def runtime():
 global _R
 if _R is None:_R=load_runtime(Path(os.environ["AION_GEOMETRY_PROGRAM_MANIFEST"]),Path(os.environ["AION_GEOMETRY_PROGRAM_ARCHIVE"]),Path(os.environ["AION_PRIVILEGED_VISUAL_MANIFEST"]),Path(os.environ["AION_PRIVILEGED_VISUAL_WEIGHTS"]),device="cuda" if torch.cuda.is_available() else "cpu")
 return _R
def propose(*,permitted,action_space,arm_id,**_):
 if arm_id=="aion_cold":q={"values":np.zeros(action_space.shape,np.float32),"policy_mode":"matched_cold"}
 elif arm_id=="aion_distilled":q=runtime().propose(np.asarray(permitted["rgb"]),np.asarray(permitted["proprioception_bounded"]),episode_id=int(permitted["episode_id"]),step=int(permitted["timestamp"]))
 else:raise RuntimeError("geometry_program_arm_mismatch")
 v=np.zeros(action_space.shape,np.float32) if q.get("abstain") else np.asarray(q["values"],np.float32).reshape(action_space.shape);v=np.clip(v,action_space.low,action_space.high)
 return {"values":v,"prediction":{"kind":q.get("policy_mode"),"teacher_used":False,"runtime_privileged_inputs":[],"abstained":bool(q.get("abstain")),"program_index":q.get("program_index")},"action_space_digest":dg({"shape":list(action_space.shape),"low":np.asarray(action_space.low).tolist(),"high":np.asarray(action_space.high).tolist(),"dtype":str(action_space.dtype)})}
