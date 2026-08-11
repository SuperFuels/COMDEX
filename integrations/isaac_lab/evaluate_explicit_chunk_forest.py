#!/usr/bin/env python3
"""Development-select an explicit-state action-chunk forest challenger."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import joblib,numpy as np
from sklearn.ensemble import ExtraTreesRegressor,RandomForestRegressor
from backend.modules.hexcore.explicit_visual_action_chunk_memory import ChromaKeypoint,make_features
from backend.modules.hexcore.object_centric_action_chunk_policy import project_world

def ix(ep,step,episodes,length):return np.flatnonzero(np.isin(ep,episodes)&(step<=250-length))
def chunk(action,indices,length):return np.stack([action[i:i+length].reshape(-1) for i in indices])
def metrics(pred,true,length):
 pred=pred.reshape(-1,length,8);true=true.reshape(-1,length,8);repeat=np.repeat(pred[:,:1],length,1);err=float(np.abs(pred-true).mean());base=float(np.abs(repeat-true).mean())
 return {'chunk_action_mae':err,'retrieved_one_step_repeated_mae':base,'improvement_over_repeated_step':float(1-err/max(base,1e-8)),'temporal_std_ratio':float(pred.std(1).mean()/(true.std(1).mean()+1e-8))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--output',required=True);p.add_argument('--model',required=True);a=p.parse_args();z=np.load(a.archive);rgb=z['rgb'];pro=z['proprioception'];act=z['action'];lab=z['privileged_training_target'];ep=z['episode'];step=z['step']
 tr=np.arange(10);dev=np.arange(10,14);sealed=np.arange(14,20);ci=np.flatnonzero(np.isin(ep,tr))[::5];detector=ChromaKeypoint.fit(rgb[ci],lab[ci,:3]);uv=detector.detect(rgb);truth,_=project_world(lab[:,:3]);candidates=[]
 for length in (8,12,16):
  ti,di=ix(ep,step,tr,length),ix(ep,step,dev,length);x=make_features(pro[ti],uv[ti],step[ti]);dx=make_features(pro[di],uv[di],step[di]);y=chunk(act,ti,length);dy=chunk(act,di,length)
  for leaf in (1,2,4,8):
   for mf in (.65,1.0):
    for family,constructor in (('extra',ExtraTreesRegressor),('random',RandomForestRegressor)):
     model=constructor(n_estimators=96,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(x,y);m=metrics(model.predict(dx),dy,length);candidates.append((m['chunk_action_mae'],-m['improvement_over_repeated_step'],family,length,leaf,mf,m))
 candidates.sort(key=lambda x:x[:2]);_,_,family,length,leaf,mf,development=candidates[0];ti,si=ix(ep,step,np.concatenate((tr,dev)),length),ix(ep,step,sealed,length);x=make_features(pro[ti],uv[ti],step[ti]);sx=make_features(pro[si],uv[si],step[si]);y=chunk(act,ti,length);sy=chunk(act,si,length);constructor=ExtraTreesRegressor if family=='extra' else RandomForestRegressor;model=constructor(n_estimators=256,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(x,y);sealed_result=metrics(model.predict(sx),sy,length);pixel=np.linalg.norm(uv[si]-truth[si],axis=1);geometry=bool(pixel.mean()<=5 and np.quantile(pixel,.9)<=7);action_gate=bool(sealed_result['chunk_action_mae']<=.35 and sealed_result['improvement_over_repeated_step']>=.2 and sealed_result['temporal_std_ratio']>=.35);Path(a.model).parent.mkdir(parents=True,exist_ok=True);joblib.dump({'detector':detector,'model':model,'chunk_length':length},a.model)
 result={'schema_version':'aion.explicit_chunk_forest_gate.v1','split':{'train':tr.tolist(),'development':dev.tolist(),'sealed':sealed.tolist()},'selected_on_development':{'family':family,'chunk_length':length,'min_samples_leaf':leaf,'max_features':mf,'metrics':development},'geometry_gate':{'passed':geometry,'mean_pixel_error':float(pixel.mean()),'p90_pixel_error':float(np.quantile(pixel,.9))},'action_chunk_gate':{'passed':action_gate,'sealed':sealed_result},'privileged_runtime_inputs':0,'physx_authorized':bool(geometry and action_gate),'cohort_note':'The sealed cohort produced aggregate metrics for failed v20/v21; v22 architecture and hyperparameters were selected only on episodes 0-13. A fresh PhysX cohort remains final authority.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
