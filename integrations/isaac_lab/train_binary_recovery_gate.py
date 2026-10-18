#!/usr/bin/env python3
"""Evidence-driven v26: RGB geometry + binary nominal/recovery routing."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import joblib,numpy as np,torch
from sklearn.ensemble import ExtraTreesClassifier,ExtraTreesRegressor
from sklearn.metrics import balanced_accuracy_score
from torch.nn import functional as F
from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.object_centric_action_chunk_policy import project_world
from backend.modules.hexcore.recovery_visual_router import RGBObjectKeypoint

def recovery_indices(ep,regime,episodes,length):
 out=[]
 for i in range(len(ep)-length+1):
  if ep[i] not in episodes or not str(regime[i]).startswith('recovery_'):continue
  if np.all(ep[i:i+length]==ep[i]) and np.all(regime[i:i+length]==regime[i]):out.append(i)
 return np.asarray(out,np.int64)
def chunks(action,indices,length):return np.stack([action[i:i+length].reshape(-1) for i in indices])
def metrics(pred,true,length):
 pred=pred.reshape(-1,length,8);true=true.reshape(-1,length,8);repeat=np.repeat(pred[:,:1],length,1);err=float(np.abs(pred-true).mean());base=float(np.abs(repeat-true).mean())
 return {'chunk_action_mae':err,'predicted_first_step_repeated_mae':base,'improvement_over_repeated_step':float(1-err/max(base,1e-8)),'temporal_std_ratio':float(pred.std(1).mean()/(true.std(1).mean()+1e-8))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--output',required=True);p.add_argument('--capsule',required=True);p.add_argument('--epochs',type=int,default=70);a=p.parse_args();z=np.load(a.archive);rgb=z['rgb'];pro=z['proprioception'];act=z['action'];labels=z['privileged_training_target'];ep=z['episode'];step=z['step'];regime=z['regime'].astype(str);truth,_=project_world(labels[:,:3]);train_ep=set(range(18));dev_ep=set(range(18,24));sealed_ep=set(range(24,30));train=np.flatnonzero(ep<18);dev=np.flatnonzero((ep>=18)&(ep<24));sealed=np.flatnonzero(ep>=24);device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu');torch.manual_seed(20260803);model=RGBObjectKeypoint().to(device);opt=torch.optim.AdamW(model.parameters(),5e-4,weight_decay=1e-4);rng=np.random.default_rng(20260803);best=None;best_error=float('inf');stale=0
 def predict(indices):
  model.eval();out=[]
  with torch.inference_mode():
   for start in range(0,len(indices),512):out.append(model(torch.from_numpy(rgb[indices[start:start+512]]).to(device)).cpu().numpy())
  return np.concatenate(out)
 for epoch in range(a.epochs):
  order=rng.permutation(train);model.train()
  for start in range(0,len(order),128):
   ids=order[start:start+128];pred=model(torch.from_numpy(rgb[ids]).to(device));target=torch.from_numpy(truth[ids]).to(device);loss=F.smooth_l1_loss(pred,target);opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);opt.step()
  if epoch % 2:
   continue
  dev_pred=predict(dev);error=float(np.linalg.norm(dev_pred-truth[dev],axis=1).mean())
  if error<best_error-.01:best_error=error;best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};stale=0
  else:stale+=1
  if stale>=14:break
 model.load_state_dict(best);model.to(device);uv=np.empty((len(ep),2),np.float32)
 for indices in (train,dev,sealed):uv[indices]=predict(indices)
 pixel=np.linalg.norm(uv[sealed]-truth[sealed],axis=1);geometry=bool(pixel.mean()<=5 and np.quantile(pixel,.9)<=7);features=make_features(pro,uv,step);binary=np.char.startswith(regime,'recovery_').astype(np.int64);router=ExtraTreesClassifier(n_estimators=256,min_samples_leaf=2,max_features=1.0,class_weight='balanced',n_jobs=-1,random_state=20260803).fit(features[np.concatenate((train,dev))],binary[np.concatenate((train,dev))]);router_pred=router.predict(features[sealed]);router_balanced=float(balanced_accuracy_score(binary[sealed],router_pred));length=8;ti,di,si=(recovery_indices(ep,regime,e,length) for e in (train_ep,dev_ep,sealed_ep));xall=features[np.concatenate((ti,di))];yall=chunks(act,np.concatenate((ti,di)),length);recovery=ExtraTreesRegressor(n_estimators=256,min_samples_leaf=2,max_features=1.0,n_jobs=-1,random_state=20260803).fit(xall,yall);sealed_metrics=metrics(recovery.predict(features[si]),chunks(act,si,length),length);action_gate=bool(sealed_metrics['chunk_action_mae']<=.35 and sealed_metrics['improvement_over_repeated_step']>=.2 and sealed_metrics['temporal_std_ratio']>=.35);router_gate=router_balanced>=.8;payload={'keypoint_state_dict':best,'router':router,'recovery_policy':recovery,'chunk_length':length};cp=Path(a.capsule);cp.parent.mkdir(parents=True,exist_ok=True);joblib.dump(payload,cp);result={'schema_version':'aion.binary_recovery_gate.v1','architecture_revision':'nominal and recovery separated; evidence did not justify forced recovery subtype separation','split':{'train_episodes':sorted(train_ep),'development_episodes':sorted(dev_ep),'sealed_episodes':sorted(sealed_ep)},'keypoint_training':{'epochs_completed':epoch+1,'best_development_mean_pixel_error':best_error,'parameters':sum(v.numel() for v in model.parameters())},'geometry_gate':{'passed':geometry,'mean_pixel_error':float(pixel.mean()),'median_pixel_error':float(np.median(pixel)),'p90_pixel_error':float(np.quantile(pixel,.9))},'binary_router_gate':{'passed':router_gate,'sealed_balanced_accuracy':router_balanced,'sealed_recovery_recall':float((router_pred[binary[sealed]==1]==1).mean()),'sealed_nominal_recall':float((router_pred[binary[sealed]==0]==0).mean())},'action_chunk_gate':{'passed':action_gate,'sealed':sealed_metrics},'privileged_runtime_inputs':0,'capsule_sha256':hashlib.sha256(cp.read_bytes()).hexdigest(),'physx_tournament_authorized':bool(geometry and router_gate and action_gate),'claim_boundary':'Passing three offline gates authorizes one fresh PhysX tournament; it does not establish manipulation competence.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
