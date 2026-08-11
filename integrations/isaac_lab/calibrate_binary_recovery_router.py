#!/usr/bin/env python3
"""Development-calibrate recovery routing without retraining physical skills."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import joblib,numpy as np,torch
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import balanced_accuracy_score
from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.recovery_visual_router import RGBObjectKeypoint

def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--source-capsule',required=True);p.add_argument('--source-result',required=True);p.add_argument('--output',required=True);p.add_argument('--capsule',required=True);a=p.parse_args();z=np.load(a.archive);rgb=z['rgb'];pro=z['proprioception'];ep=z['episode'];step=z['step'];regime=z['regime'].astype(str);source=joblib.load(a.source_capsule);source_result=json.load(open(a.source_result));device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu');model=RGBObjectKeypoint();model.load_state_dict(source['keypoint_state_dict']);model.to(device).eval();uv=[]
 with torch.inference_mode():
  for start in range(0,len(rgb),512):uv.append(model(torch.from_numpy(rgb[start:start+512]).to(device)).cpu().numpy())
 uv=np.concatenate(uv);features=make_features(pro,uv,step);target=np.char.startswith(regime,'recovery_').astype(np.int64);train=np.flatnonzero(ep<18);dev=np.flatnonzero((ep>=18)&(ep<24));sealed=np.flatnonzero(ep>=24);candidates=[]
 for leaf in (1,2,4,8):
  for mf in (.65,1.0):
   candidate=ExtraTreesClassifier(n_estimators=96,min_samples_leaf=leaf,max_features=mf,class_weight='balanced',n_jobs=-1,random_state=20260803).fit(features[train],target[train]);prob=candidate.predict_proba(features[dev])[:,1]
   for threshold in np.linspace(.05,.75,71):
    pred=(prob>=threshold).astype(np.int64);score=float(balanced_accuracy_score(target[dev],pred));recall=float((pred[target[dev]==1]==1).mean());nominal=float((pred[target[dev]==0]==0).mean());candidates.append((-score,-min(recall,nominal),leaf,mf,float(threshold),score,recall,nominal))
 candidates.sort();_,_,leaf,mf,threshold,development_accuracy,development_recall,development_nominal=candidates[0];fit=np.concatenate((train,dev));router=ExtraTreesClassifier(n_estimators=256,min_samples_leaf=leaf,max_features=mf,class_weight='balanced',n_jobs=-1,random_state=20260803).fit(features[fit],target[fit]);prob=router.predict_proba(features[sealed])[:,1];pred=(prob>=threshold).astype(np.int64);balanced=float(balanced_accuracy_score(target[sealed],pred));recovery=float((pred[target[sealed]==1]==1).mean());nominal=float((pred[target[sealed]==0]==0).mean());passed=bool(balanced>=.8 and recovery>=.7 and nominal>=.8);payload={**source,'router':router,'router_threshold':threshold};cp=Path(a.capsule);cp.parent.mkdir(parents=True,exist_ok=True);joblib.dump(payload,cp);result={'schema_version':'aion.calibrated_binary_recovery_router.v1','source_gates':{'geometry':source_result['geometry_gate'],'action_chunk':source_result['action_chunk_gate']},'selected_on_development':{'min_samples_leaf':leaf,'max_features':mf,'threshold':threshold,'balanced_accuracy':development_accuracy,'recovery_recall':development_recall,'nominal_recall':development_nominal},'sealed_router_gate':{'passed':passed,'balanced_accuracy':balanced,'recovery_recall':recovery,'nominal_recall':nominal,'requirements':['balanced >=0.80','recovery >=0.70','nominal >=0.80']},'all_offline_gates_passed':bool(source_result['geometry_gate']['passed'] and source_result['action_chunk_gate']['passed'] and passed),'physx_tournament_authorized':bool(source_result['geometry_gate']['passed'] and source_result['action_chunk_gate']['passed'] and passed),'capsule_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'claim_boundary':'Calibrated routing plus prior fresh geometry/action gates authorize one matched fresh-reset tournament only.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
