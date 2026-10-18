"""Teacher-free geometry-routed episodic manipulation programs."""
from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import torch
from .privileged_visual_distillation_policy import load_runtime as load_visual

SCHEMA="aion.geometry_routed_program_memory.v1"
def sha256(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

@dataclass
class Runtime:
    visual: object; manifest:dict; programs:dict; chosen:int|None=None; episode:int|None=None
    def propose(self,rgb,proprioception,*,episode_id:int,step:int):
        if self.episode!=episode_id or step==0:
            self.episode=episode_id; self.chosen=None
            result=self.visual.propose(rgb,proprioception,episode_id=episode_id,step=0)
            if result.get("abstain"): return result
            belief=np.asarray(result["belief"],np.float32)
            distances=np.linalg.norm(self.programs["prototype"]-belief[None],axis=1)
            self.chosen=int(np.argmin(distances))
        if self.chosen is None or step>=int(self.programs["length"][self.chosen]):
            return {"abstain":True,"reason":"program_exhausted"}
        return {"abstain":False,"values":self.programs["action"][self.chosen,step].astype(np.float32),
                "teacher_used":False,"policy_mode":"visual_geometry_routed_coherent_program",
                "program_index":self.chosen,"capsule_digest":self.manifest["capsule_digest"]}

def load_runtime(manifest_path:Path,archive_path:Path,visual_manifest:Path,visual_weights:Path,*,device="cpu"):
    m=json.loads(manifest_path.read_text()); unsigned={k:v for k,v in m.items() if k!="capsule_digest"}
    if m.get("schema_version")!=SCHEMA or m.get("capsule_digest")!=digest(unsigned): raise ValueError("program_manifest_integrity_failure")
    if sha256(archive_path)!=m.get("archive_sha256"): raise ValueError("program_archive_integrity_failure")
    with np.load(archive_path,allow_pickle=False) as z: p={k:z[k] for k in ("prototype","action","length")}
    return Runtime(load_visual(visual_manifest,visual_weights,device=device),m,p)
