#!/usr/bin/env python3
"""Fuse successful reset diversity with student-visited recovery chunks."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import joblib,numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.object_centric_action_chunk_policy import project_world

def ix(ep,step,episodes,length):return np.flatnonzero(np.isin(ep,episodes)&(step<=250-length))
def chunks(action,indices,length):return np.stack([action[i:i+length].reshape(-1) for i in indices])
def metrics(pred,true,length):
 pred=pred.reshape(-1,length,8);true=true.reshape(-1,length,8);repeat=np.repeat(pred[:,:1],length,1);err=float(np.abs(pred-true).mean());base=float(np.abs(repeat-true).mean())
 return {'chunk_action_mae':err,'predicted_first_step_repeated_mae':base,'improvement_over_repeated_step':float(1-err/max(base,1e-8)),'temporal_std_ratio':float(pred.std(1).mean()/(true.std(1).mean()+1e-8))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--teacher-archive',required=True);p.add_argument('--teacher-receipt',required=True);p.add_argument('--recovery-archive',required=True);p.add_argument('--detector',required=True);p.add_argument('--output',required=True);p.add_argument('--model',required=True);a=p.parse_args();teacher=np.load(a.teacher_archive);recovery=np.load(a.recovery_archive);receipt=json.load(open(a.teacher_receipt));success=np.asarray(sorted(int(x['episode']) for x in receipt['outcomes'] if x['success']));detector=joblib.load(a.detector)['detector'];length=8
 tep,tstep=teacher['episode'],teacher['step'];rep,rstep=recovery['episode'],recovery['step'];tix=ix(tep,tstep,success,length);train_recovery=ix(rep,rstep,np.arange(10),length);dev=ix(rep,rstep,np.arange(10,14),length);sealed=ix(rep,rstep,np.arange(14,20),length)
 tuv=detector.detect(teacher['rgb'][tix]);ruv=detector.detect(recovery['rgb']);tx=make_features(teacher['proprioception'][tix],tuv,tstep[tix]);rx=make_features(recovery['proprioception'][train_recovery],ruv[train_recovery],rstep[train_recovery]);x=np.concatenate((tx,rx));y=np.concatenate((chunks(teacher['action'],tix,length),chunks(recovery['action'],train_recovery,length)));dx=make_features(recovery['proprioception'][dev],ruv[dev],rstep[dev]);dy=chunks(recovery['action'],dev,length);sx=make_features(recovery['proprioception'][sealed],ruv[sealed],rstep[sealed]);sy=chunks(recovery['action'],sealed,length)
 candidates=[]
 for leaf in (1,2,4,8):
  for mf in (.65,1.0):
   model=ExtraTreesRegressor(n_estimators=96,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(x,y);m=metrics(model.predict(dx),dy,length);candidates.append((m['chunk_action_mae'],-m['improvement_over_repeated_step'],leaf,mf,m))
 candidates.sort(key=lambda z:z[:2]);_,_,leaf,mf,development=candidates[0];model=ExtraTreesRegressor(n_estimators=256,min_samples_leaf=leaf,max_features=mf,n_jobs=-1,random_state=20260803).fit(x,y);sealed_result=metrics(model.predict(sx),sy,length);truth,_=project_world(recovery['privileged_training_target'][sealed,:3]);pixel=np.linalg.norm(ruv[sealed]-truth,axis=1);geometry=bool(pixel.mean()<=5 and np.quantile(pixel,.9)<=7);action_gate=bool(sealed_result['chunk_action_mae']<=.35 and sealed_result['improvement_over_repeated_step']>=.2 and sealed_result['temporal_std_ratio']>=.35);Path(a.model).parent.mkdir(parents=True,exist_ok=True);joblib.dump({'detector':detector,'model':model,'chunk_length':length},a.model);result={'schema_version':'aion.teacher_recovery_chunk_gate.v1','training_authority':{'successful_teacher_resets':len(success),'teacher_chunks':len(tix),'student_visited_recovery_episodes':10,'recovery_chunks':len(train_recovery)},'development_recovery_episodes':[10,11,12,13],'sealed_recovery_episodes':[14,15,16,17,18,19],'selected_on_development':{'min_samples_leaf':leaf,'max_features':mf,'metrics':development},'geometry_gate':{'passed':geometry,'mean_pixel_error':float(pixel.mean()),'p90_pixel_error':float(np.quantile(pixel,.9))},'action_chunk_gate':{'passed':action_gate,'sealed':sealed_result},'privileged_runtime_inputs':0,'physx_authorized':bool(geometry and action_gate),'claim_boundary':'Offline archived evidence authorizes only one fresh-reset PhysX tournament; it is not online manipulation competence.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
