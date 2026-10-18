"""Teacher-removed Isaac adapter for asymmetric visual apprenticeship."""
from __future__ import annotations
import hashlib,json,os
from pathlib import Path
import numpy as np
import torch
from backend.modules.hexcore.privileged_visual_distillation_policy import load_runtime
_CACHE={}
def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _runtime():
    m,w=Path(os.environ["AION_PRIVILEGED_VISUAL_MANIFEST"]),Path(os.environ["AION_PRIVILEGED_VISUAL_WEIGHTS"]); key=hashlib.sha256(m.read_bytes()+w.read_bytes()).hexdigest()
    if key not in _CACHE: _CACHE.clear(); _CACHE[key]=load_runtime(m,w,device="cuda" if torch.cuda.is_available() else "cpu")
    return _CACHE[key]
def propose(*,permitted,action_space,arm_id,**_):
    if arm_id=="aion_cold": result={"abstain":False,"values":np.zeros(action_space.shape,np.float32),"policy_mode":"matched_cold"}
    elif arm_id=="aion_distilled": result=_runtime().propose(np.asarray(permitted["rgb"]),np.asarray(permitted["proprioception_bounded"]),episode_id=int(permitted["episode_id"]),step=int(permitted["timestamp"]))
    else: raise RuntimeError("privileged_distillation_arm_mismatch")
    values=np.zeros(action_space.shape,np.float32) if result.get("abstain") else np.asarray(result["values"],np.float32).reshape(action_space.shape)
    values=np.clip(values,action_space.low,action_space.high).astype(np.float32)
    return {"values":values,"prediction":{"kind":result.get("policy_mode"),"teacher_used":False,"runtime_privileged_inputs":[],"abstained":bool(result.get("abstain")),"reason":result.get("reason")},"action_space_digest":_digest({"shape":list(action_space.shape),"low":np.asarray(action_space.low).tolist(),"high":np.asarray(action_space.high).tolist(),"dtype":str(action_space.dtype)})}
