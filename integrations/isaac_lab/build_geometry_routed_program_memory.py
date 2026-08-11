#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import numpy as np
from backend.modules.hexcore.geometry_routed_program_memory import SCHEMA,digest,sha256
p=argparse.ArgumentParser();p.add_argument("--receipt",required=True);p.add_argument("--source",required=True);p.add_argument("--visual-manifest",required=True);p.add_argument("--manifest",required=True);p.add_argument("--archive",required=True);a=p.parse_args()
r=json.load(open(a.receipt)); vm=json.load(open(a.visual_manifest))
if sha256(Path(a.source))!=r["private_trajectory"]["sha256"] or not r["audit"]["privileged_training_labels_quarantined"]: raise ValueError("authority_failure")
success={int(x["episode"]) for x in r["outcomes"] if x["success"]}
with np.load(a.source,allow_pickle=False) as z:
 programs=[]
 for eid in sorted(success):
  ix=np.flatnonzero(z["episode"]==eid);ix=ix[np.argsort(z["step"][ix])]
  label=(z["privileged_training_target"][ix[0]]-np.asarray(vm["label_mean"]))/np.asarray(vm["label_scale"])
  programs.append((label.astype(np.float32),z["action"][ix].astype(np.float32)))
length=np.asarray([len(x[1]) for x in programs],np.int32); actions=np.zeros((len(programs),int(length.max()),programs[0][1].shape[1]),np.float32)
for i,x in enumerate(programs):actions[i,:len(x[1])]=x[1]
out=Path(a.archive);out.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(out,prototype=np.stack([x[0] for x in programs]),action=actions,length=length)
m={"schema_version":SCHEMA,"archive_sha256":sha256(out),"program_count":len(programs),"training_label_role":"retained_prototype_only_not_runtime_input","runtime_privileged_inputs":[],"visual_capsule_digest":vm["capsule_digest"],"teacher_available_at_runtime":False,"prospective_physx_required":True};m["capsule_digest"]=digest(m);Path(a.manifest).write_text(json.dumps(m,indent=2,sort_keys=True));print(json.dumps(m,sort_keys=True))
