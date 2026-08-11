#!/usr/bin/env python3
"""Select and compile a protected/corrective embodied experience router."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from backend.modules.hexcore.episodic_embodied_skill_memory import spatial_state
from backend.modules.hexcore.governed_embodied_experience_router import SCHEMA, VISUAL_DIM, digest, sha256

def load(pair: str, cohort: int):
    receipt_name, archive_name = pair.split("=",1); rp,ap=Path(receipt_name),Path(archive_name)
    receipt=json.loads(rp.read_text()); audit=receipt.get('audit') or {}
    if any(audit.get(k) is not True for k in ('completed_without_failure','student_privileged_fields_absent','commit_before_act_verified','teacher_removed_evaluation_required')): raise ValueError('authority_incomplete')
    if sha256(ap)!=receipt['private_trajectory']['sha256']: raise ValueError('archive_integrity_failure')
    outcomes={int(x['episode']):bool(x.get('success')) for x in receipt['outcomes']}
    with np.load(ap,allow_pickle=False) as raw: arrays={k:raw[k] for k in ('rgb','proprioception','action','episode','step')}
    return receipt,arrays,outcomes,cohort,audit.get('dagger_teacher_labels_verified') is True

def main():
    p=argparse.ArgumentParser();p.add_argument('--authority',action='append',required=True);p.add_argument('--manifest',required=True);p.add_argument('--archive',required=True);a=p.parse_args()
    inputs=[load(pair,i) for i,pair in enumerate(a.authority)]
    proprio=np.concatenate([x[1]['proprioception'] for x in inputs]).astype(np.float32);mean=proprio.mean(0);scale=proprio.std(0);scale[scale<1e-5]=1
    low,high=proprio.min(0),proprio.max(0);pm=np.maximum((high-low)*.2,.05)
    rows=[]; source_hashes=[]
    for receipt,raw,outcomes,cohort,is_dagger in inputs:
      source_hashes.append(hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()).hexdigest())
      eligible=set(outcomes) if is_dagger else {e for e,s in outcomes.items() if s}
      for episode in sorted(eligible):
        idx=np.flatnonzero(raw['episode']==episode);idx=idx[np.argsort(raw['step'][idx])];prev=None
        for i in idx:
          image=raw['rgb'][i,...,:3];prev=image if prev is None else prev
          state=spatial_state(image,prev,raw['proprioception'][i],int(raw['step'][i]),proprio_mean=mean,proprio_scale=scale)
          # Teacher demonstrations and independently successful corrective
          # episodes are immutable protected experience.
          protected=(not is_dagger) or outcomes[episode]
          rows.append((state,raw['action'][i].astype(np.float32),int(raw['step'][i]),protected,cohort,episode));prev=image
    # Episode-disjoint selection: last quarter of each cohort is never in the
    # candidate memory while router hyperparameters are chosen.
    train=[];held=[]
    for cohort in sorted({r[4] for r in rows}):
      episodes=sorted({r[5] for r in rows if r[4]==cohort});cut=max(1,len(episodes)//4);hold=set(episodes[-cut:])
      (held if False else train)
      for r in [x for x in rows if x[4]==cohort]: (held if r[5] in hold else train).append(r)
    action_scale=np.std(np.vstack([r[1] for r in train]),0);action_scale[action_scale<1e-4]=1
    by_step={}
    for row in train: by_step.setdefault(row[2],[]).append(row)
    validation=[]
    # A deterministic temporal subsample keeps selection bounded while
    # preserving every manipulation phase family across held-out episodes.
    for q in [row for row in held if row[2] % 5 == 0]:
      candidates=[]
      for phase in range(q[2]-1,q[2]+2): candidates.extend(by_step.get(phase,[]))
      if not candidates: continue
      matrix=np.vstack([row[0] for row in candidates])
      dv=np.mean((matrix[:,:VISUAL_DIM]-q[0][:VISUAL_DIM])**2,axis=1)
      dp=np.mean((matrix[:,VISUAL_DIM:-1]-q[0][VISUAL_DIM:-1])**2,axis=1)
      validation.append((q,candidates,dv,dp))
    configs=[]
    for vw in (.5,1.,2.):
      for pw in (.5,1.,2.,4.):
       for margin in (.5,.75,1.,1.25):
        errors=[];groups={}
        for q,candidates,dv,dp in validation:
          costs=vw*dv+pw*dp
          pidx=np.asarray([i for i,r in enumerate(candidates) if r[3]],dtype=int)
          cidx=np.asarray([i for i,r in enumerate(candidates) if not r[3]],dtype=int)
          if not len(pidx): continue
          pi=int(pidx[np.argmin(costs[pidx])]);selected,pc=candidates[pi],float(costs[pi])
          if len(cidx):
            ci=int(cidx[np.argmin(costs[cidx])]);correction,cc=candidates[ci],float(costs[ci])
            if cc<pc*margin and np.linalg.norm(correction[1]-selected[1])<=8.: selected=correction
          error=float(np.mean(((selected[1]-q[1])/action_scale)**2));errors.append(error);groups.setdefault(q[4],[]).append(error)
        configs.append({'visual_weight':vw,'proprio_weight':pw,'correction_margin':margin,'mean_mse':float(np.mean(errors)),'worst_cohort_mse':max(float(np.mean(v)) for v in groups.values())})
    champion=min(configs,key=lambda c:(c['worst_cohort_mse'],c['mean_mse']))
    states=np.vstack([r[0] for r in rows]);actions=np.vstack([r[1] for r in rows]);steps=np.asarray([r[2] for r in rows],dtype=np.int16);protected=np.asarray([r[3] for r in rows],dtype=bool)
    out=Path(a.archive);out.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(out,states=states.astype(np.float16),actions=actions,steps=steps,protected=protected)
    al,ah=actions.min(0),actions.max(0);am=np.maximum((ah-al)*.01,1e-3)
    manifest={'schema_version':SCHEMA,'archive_sha256':sha256(out),'source_receipt_sha256':sorted(source_hashes),'verified_transition_count':len(rows),'protected_transition_count':int(protected.sum()),'corrective_transition_count':int((~protected).sum()),'proprio_mean':mean.tolist(),'proprio_scale':scale.tolist(),'proprio_low':(low-pm).tolist(),'proprio_high':(high+pm).tolist(),'action_low':(al-am).tolist(),'action_high':(ah+am).tolist(),'phase_window':1,'maximum_action_disagreement':8.,'ood_radius':12.,'selection':champion,'visual_weight':champion['visual_weight'],'proprio_weight':champion['proprio_weight'],'correction_margin':champion['correction_margin'],'candidate_count':len(configs),'teacher_removed_execution_required':True}
    manifest['capsule_digest']=digest(manifest);Path(a.manifest).write_text(json.dumps(manifest,indent=2,sort_keys=True));print(json.dumps({'capsule_digest':manifest['capsule_digest'],'states':len(rows),'protected':int(protected.sum()),'corrective':int((~protected).sum()),'selection':champion},sort_keys=True))
if __name__=='__main__':main()
