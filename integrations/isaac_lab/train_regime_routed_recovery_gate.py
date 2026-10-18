#!/usr/bin/env python3
"""Fresh-holdout Gate B for separately routed contact-recovery programs."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import joblib,numpy as np
from sklearn.ensemble import ExtraTreesClassifier,ExtraTreesRegressor
from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.object_centric_action_chunk_policy import project_world

KINDS=("pre_grasp","grasp_slip","lift_instability")
def eligible(ep,regime,episodes,length):
 out=[]
 for i in range(len(ep)-length+1):
  if ep[i] not in episodes or not str(regime[i]).startswith('recovery_'):continue
  if np.all(ep[i:i+length]==ep[i]) and np.all(regime[i:i+length]==regime[i]):out.append(i)
 return np.asarray(out,np.int64)
def chunks(action,indices,length):return np.stack([action[i:i+length].reshape(-1) for i in indices])
def kind(regime):return np.asarray([KINDS.index(str(x).removeprefix('recovery_')) for x in regime],np.int64)
def metrics(pred,true,length):
 pred=pred.reshape(-1,length,8);true=true.reshape(-1,length,8);repeat=np.repeat(pred[:,:1],length,1);err=float(np.abs(pred-true).mean());base=float(np.abs(repeat-true).mean())
 return {'chunk_action_mae':err,'predicted_first_step_repeated_mae':base,'improvement_over_repeated_step':float(1-err/max(base,1e-8)),'temporal_std_ratio':float(pred.std(1).mean()/(true.std(1).mean()+1e-8))}
def fit_routed(x,y,k,leaf,mf,trees=128):return {n:ExtraTreesRegressor(n_estimators=trees,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803+n).fit(x[k==n],y[k==n]) for n in range(3)}
def route_predict(models,x,predicted):return np.stack([models[int(k)].predict(row[None])[0] for row,k in zip(x,predicted)])
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--detector',required=True);p.add_argument('--output',required=True);p.add_argument('--capsule',required=True);a=p.parse_args();z=np.load(a.archive);rgb=z['rgb'];pro=z['proprioception'];act=z['action'];labels=z['privileged_training_target'];ep=z['episode'];step=z['step'];regime=z['regime'].astype(str);detector=joblib.load(a.detector)['detector'];uv=detector.detect(rgb);length=8;train_ep=set(range(18));dev_ep=set(range(18,24));sealed_ep=set(range(24,30));ti,di,si=(eligible(ep,regime,e,length) for e in (train_ep,dev_ep,sealed_ep));features=make_features(pro,uv,step);x,dx,sx=features[ti],features[di],features[si];y,dy,sy=chunks(act,ti,length),chunks(act,di,length),chunks(act,si,length);tk,dk,sk=kind(regime[ti]),kind(regime[di]),kind(regime[si]);candidates=[]
 for leaf in (1,2,4):
  for mf in (.65,1.0):
   classifier=ExtraTreesClassifier(n_estimators=128,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(x,tk);models=fit_routed(x,y,tk,leaf,mf);predicted=classifier.predict(dx);m=metrics(route_predict(models,dx,predicted),dy,length);candidates.append((m['chunk_action_mae'],-m['improvement_over_repeated_step'],leaf,mf,m,float((predicted==dk).mean())))
 candidates.sort(key=lambda row:row[:2]);_,_,leaf,mf,development,development_router_accuracy=candidates[0];train_all=np.concatenate((ti,di));xall=features[train_all];yall=chunks(act,train_all,length);kall=kind(regime[train_all]);classifier=ExtraTreesClassifier(n_estimators=256,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(xall,kall);models=fit_routed(xall,yall,kall,leaf,mf,256);predicted=classifier.predict(sx);routed_prediction=route_predict(models,sx,predicted);sealed=metrics(routed_prediction,sy,length);router_accuracy=float((predicted==sk).mean())
 pooled=ExtraTreesRegressor(n_estimators=256,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(xall,yall);pooled_result=metrics(pooled.predict(sx),sy,length);truth,_=project_world(labels[si,:3]);pixel=np.linalg.norm(uv[si]-truth,axis=1);geometry=bool(pixel.mean()<=5 and np.quantile(pixel,.9)<=7);action_gate=bool(sealed['chunk_action_mae']<=.35 and sealed['improvement_over_repeated_step']>=.2 and sealed['temporal_std_ratio']>=.35 and sealed['chunk_action_mae']<pooled_result['chunk_action_mae'] and router_accuracy>=.8);payload={'detector':detector,'router':classifier,'recovery_models':models,'chunk_length':length,'regimes':KINDS};cp=Path(a.capsule);cp.parent.mkdir(parents=True,exist_ok=True);joblib.dump(payload,cp);result={'schema_version':'aion.regime_routed_recovery_gate.v1','split':{'train_episodes':sorted(train_ep),'development_episodes':sorted(dev_ep),'sealed_episodes':sorted(sealed_ep)},'samples':{'train':len(ti),'development':len(di),'sealed':len(si)},'selected_on_development':{'min_samples_leaf':leaf,'max_features':mf,'router_accuracy':development_router_accuracy,'metrics':development},'geometry_gate':{'passed':geometry,'mean_pixel_error':float(pixel.mean()),'p90_pixel_error':float(np.quantile(pixel,.9))},'recovery_router':{'sealed_accuracy':router_accuracy,'regime_counts':{KINDS[n]:int((sk==n).sum()) for n in range(3)}},'pooled_control':pooled_result,'action_chunk_gate':{'passed':action_gate,'sealed':sealed,'requirements':['MAE <=0.35','>=20% improvement','>=0.35 temporal ratio','better than pooled','router accuracy >=80%']},'privileged_runtime_inputs':0,'capsule_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'physx_tournament_authorized':bool(geometry and action_gate),'claim_boundary':'Fresh offline recovery holdout authorizes a teacher-removed PhysX challenger; it does not establish manipulation success.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
