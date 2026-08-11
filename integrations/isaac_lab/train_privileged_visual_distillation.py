#!/usr/bin/env python3
"""Train an RGB runtime using quarantined simulator geometry as auxiliary supervision."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
from backend.modules.hexcore.privileged_visual_distillation_policy import (
    SCHEMA, PrivilegedVisualPolicy, digest, sha256)


def load_authority(receipt_path: Path, archive_path: Path):
    receipt = json.loads(receipt_path.read_text()); audit = receipt.get("audit", {})
    if not (audit.get("privileged_training_labels_quarantined") is True and
            audit.get("privileged_training_labels_exposed_to_behavior") is False and
            audit.get("completed_without_failure") is True):
        raise ValueError("asymmetric_authority_quarantine_failure")
    if sha256(archive_path) != receipt["private_trajectory"]["sha256"]:
        raise ValueError("authority_archive_integrity_failure")
    with np.load(archive_path, allow_pickle=False) as source:
        data = {k: source[k] for k in ("rgb", "proprioception", "action", "episode", "step", "privileged_training_target")}
    successful = ({int(x["episode"]) for x in receipt["outcomes"]}
                  if audit.get("dagger_teacher_labels_verified") is True else
                  {int(x["episode"]) for x in receipt["outcomes"] if x.get("success")})
    episodes=[]
    for eid in sorted(successful):
        ix=np.flatnonzero(data["episode"]==eid); ix=ix[np.argsort(data["step"][ix])]
        if len(ix): episodes.append(tuple(data[k][ix] for k in ("rgb","proprioception","action","privileged_training_target")))
    return receipt, episodes


def make_batch(episodes, rng, batch_size=8, length=96):
    chosen=rng.choice(len(episodes), min(batch_size,len(episodes)), replace=False)
    shape=(len(chosen),length)
    rgb=np.zeros(shape+(96,128,3),np.uint8); prop=np.zeros(shape+(episodes[0][1].shape[-1],),np.float32)
    act=np.zeros(shape+(episodes[0][2].shape[-1],),np.float32); lab=np.zeros(shape+(episodes[0][3].shape[-1],),np.float32); valid=np.zeros(shape,bool)
    for row,index in enumerate(chosen):
        item=episodes[index]; start=int(rng.integers(0,max(1,len(item[0])-length+1))); n=min(length,len(item[0])-start)
        rgb[row,:n],prop[row,:n],act[row,:n],lab[row,:n]=[x[start:start+n] for x in item]; valid[row,:n]=1
    return rgb,prop,act,lab,valid


def main():
    p=argparse.ArgumentParser(); p.add_argument("--authority",action="append",required=True); p.add_argument("--manifest",required=True); p.add_argument("--weights",required=True)
    p.add_argument("--epochs",type=int,default=180); p.add_argument("--batches-per-epoch",type=int,default=12); a=p.parse_args()
    receipts=[]; episodes=[]
    for pair in a.authority:
        r,z=pair.split("=",1); receipt,seq=load_authority(Path(r),Path(z)); receipts.append(receipt); episodes.extend(seq)
    actions=np.concatenate([x[2] for x in episodes]); props=np.concatenate([x[1] for x in episodes]); labels=np.concatenate([x[3] for x in episodes])
    am,asc=actions.mean(0),actions.std(0); asc[asc<1e-4]=1; lm,lsc=labels.mean(0),labels.std(0); lsc[lsc<1e-4]=1
    torch.manual_seed(161803); rng=np.random.default_rng(161803); dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model=PrivilegedVisualPolicy(props.shape[1],actions.shape[1],labels.shape[1]).to(dev); opt=torch.optim.AdamW(model.parameters(),3e-4,weight_decay=1e-5)
    losses=[]
    for epoch in range(a.epochs):
        current=[]
        for _ in range(a.batches_per_epoch):
            rgb,pro,act,lab,val=make_batch(episodes,rng); prior=np.concatenate((np.zeros_like(act[:,:1]),act[:,:-1]),1)
            # Corrupt teacher history on half the sequences to reduce exposure bias.
            prior[rng.random(prior.shape[:2])<.15]=0
            tt=lambda x:torch.from_numpy(x).to(dev)
            pred,belief=model.sequence(tt(rgb),tt(pro),tt((prior-am)/asc),tt(val)); target=tt((act-am)/asc); geometry=tt((lab-lm)/lsc); mask=tt(val).unsqueeze(-1)
            action_loss=F.smooth_l1_loss(pred[mask.expand_as(pred)],target[mask.expand_as(target)])
            belief_loss=F.smooth_l1_loss(belief[mask.expand_as(belief)],geometry[mask.expand_as(geometry)])
            loss=action_loss+1.25*belief_loss; opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),5); opt.step(); current.append(float(loss.detach().cpu()))
        losses.append(float(np.mean(current)))
    weights=Path(a.weights); weights.parent.mkdir(parents=True,exist_ok=True); torch.save(model.cpu().eval().state_dict(),weights)
    lo,hi=actions.min(0),actions.max(0); margin=np.maximum((hi-lo)*.02,1e-3); plo,phi=props.min(0),props.max(0); pm=np.maximum((phi-plo)*.25,.05)
    manifest={"schema_version":SCHEMA,"weights_sha256":sha256(weights),"proprio_dim":int(props.shape[1]),"action_dim":int(actions.shape[1]),"label_dim":int(labels.shape[1]),"hidden_dim":256,
      "action_mean":am.tolist(),"action_scale":asc.tolist(),"action_low":(lo-margin).tolist(),"action_high":(hi+margin).tolist(),"proprio_low":(plo-pm).tolist(),"proprio_high":(phi+pm).tolist(),
      "label_mean":lm.tolist(),"label_scale":lsc.tolist(),"verified_episodes":len(episodes),"verified_transitions":int(sum(len(x[0]) for x in episodes)),"training_epochs":a.epochs,"final_loss":losses[-1],"minimum_loss":min(losses),
      "training_only_privileged_labels":["object_position","goal_pose"],"runtime_inputs":["rgb","bounded_proprioception","previous_action"],"runtime_privileged_inputs":[],"teacher_available_at_runtime":False,
      "authority_receipts":[hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest() for r in receipts],"prospective_physx_evaluation_required":True,
      "claim_boundary":"Auxiliary geometry fit is not control competence; teacher-removed PhysX outcomes alone authorize promotion."}
    manifest["capsule_digest"]=digest(manifest); Path(a.manifest).write_text(json.dumps(manifest,indent=2,sort_keys=True)); print(json.dumps({k:manifest[k] for k in ("capsule_digest","verified_episodes","verified_transitions","final_loss")},sort_keys=True))
if __name__=="__main__": main()
