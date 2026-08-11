#!/usr/bin/env python3
"""Train a smooth action-chunk policy after explicit RGB geometry is earned."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import joblib,numpy as np,torch
from torch import nn
from torch.nn import functional as F
from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.object_centric_action_chunk_policy import project_world

class ChunkPolicy(nn.Module):
 def __init__(self,input_dim=22,output_dim=64):
  super().__init__();self.net=nn.Sequential(nn.Linear(input_dim,256),nn.LayerNorm(256),nn.GELU(),nn.Linear(256,384),nn.GELU(),nn.Linear(384,384),nn.GELU(),nn.Linear(384,output_dim))
 def forward(self,x):return self.net(x)
def ix(ep,step,episodes,length):return np.flatnonzero(np.isin(ep,episodes)&(step<=250-length))
def chunk(action,indices,length):return np.stack([action[i:i+length].reshape(-1) for i in indices])
def metrics(pred,true,length):
 pred=pred.reshape(-1,length,8);true=true.reshape(-1,length,8);repeat=np.repeat(pred[:,:1],length,1);err=float(np.abs(pred-true).mean());base=float(np.abs(repeat-true).mean())
 return {'chunk_action_mae':err,'predicted_first_step_repeated_mae':base,'improvement_over_repeated_step':float(1-err/max(base,1e-8)),'temporal_std_ratio':float(pred.std(1).mean()/(true.std(1).mean()+1e-8))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--detector',required=True);p.add_argument('--output',required=True);p.add_argument('--weights',required=True);p.add_argument('--epochs',type=int,default=160);a=p.parse_args();z=np.load(a.archive);rgb=z['rgb'];pro=z['proprioception'];act=z['action'];lab=z['privileged_training_target'];ep=z['episode'];step=z['step'];detector=joblib.load(a.detector)['detector'];uv=detector.detect(rgb);truth_uv,_=project_world(lab[:,:3]);length=8;tr=np.arange(10);dev=np.arange(10,14);sealed=np.arange(14,20);ti,di,si=(ix(ep,step,e,length) for e in (tr,dev,sealed));x=make_features(pro[ti],uv[ti],step[ti]);dx=make_features(pro[di],uv[di],step[di]);sx=make_features(pro[si],uv[si],step[si]);y=chunk(act,ti,length);dy=chunk(act,di,length);sy=chunk(act,si,length);xm,xs=x.mean(0),x.std(0);xs[xs<1e-4]=1;ym,ys=y.mean(0),y.std(0);ys[ys<1e-4]=1
 device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu');torch.manual_seed(20260803);model=ChunkPolicy(output_dim=length*8).to(device);opt=torch.optim.AdamW(model.parameters(),lr=7e-4,weight_decay=2e-4);tx=torch.from_numpy(((x-xm)/xs).astype(np.float32));ty=torch.from_numpy(((y-ym)/ys).astype(np.float32));vdx=torch.from_numpy(((dx-xm)/xs).astype(np.float32)).to(device);order=np.arange(len(x));rng=np.random.default_rng(20260803);best=None;best_mae=float('inf');stale=0
 for epoch in range(a.epochs):
  model.train();rng.shuffle(order)
  for start in range(0,len(order),128):
   ids=order[start:start+128];pred=model(tx[ids].to(device));loss=F.smooth_l1_loss(pred,ty[ids].to(device));opt.zero_grad(set_to_none=True);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5);opt.step()
  model.eval()
  with torch.inference_mode():vp=model(vdx).cpu().numpy()*ys+ym
  mae=float(np.abs(vp-dy).mean())
  if mae<best_mae-1e-5:best_mae=mae;best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()};stale=0
  else:stale+=1
  if stale>=24:break
 model.load_state_dict(best);model.to(device).eval()
 with torch.inference_mode():dp=model(vdx).cpu().numpy()*ys+ym;sp=model(torch.from_numpy(((sx-xm)/xs).astype(np.float32)).to(device)).cpu().numpy()*ys+ym
 development=metrics(dp,dy,length);sealed_result=metrics(sp,sy,length);pixel=np.linalg.norm(uv[si]-truth_uv[si],axis=1);geometry=bool(pixel.mean()<=5 and np.quantile(pixel,.9)<=7);action_gate=bool(sealed_result['chunk_action_mae']<=.35 and sealed_result['improvement_over_repeated_step']>=.2 and sealed_result['temporal_std_ratio']>=.35);payload={'state_dict':best,'x_mean':xm,'x_scale':xs,'y_mean':ym,'y_scale':ys,'detector':detector,'chunk_length':length};wp=Path(a.weights);wp.parent.mkdir(parents=True,exist_ok=True);torch.save(payload,wp);result={'schema_version':'aion.explicit_state_chunk_policy_gate.v1','split':{'train':tr.tolist(),'development':dev.tolist(),'sealed':sealed.tolist()},'training':{'epochs_completed':epoch+1,'best_development_mae':best_mae,'parameters':sum(v.numel() for v in model.parameters())},'development':development,'geometry_gate':{'passed':geometry,'mean_pixel_error':float(pixel.mean()),'p90_pixel_error':float(np.quantile(pixel,.9))},'action_chunk_gate':{'passed':action_gate,'sealed':sealed_result},'runtime_inputs':['rgb','bounded_proprioception','mission_lift_cube'],'privileged_runtime_inputs':0,'weights_sha256':hashlib.sha256(wp.read_bytes()).hexdigest(),'physx_authorized':bool(geometry and action_gate),'claim_boundary':'Offline cohort is development-owned and previously aggregate-exposed; success authorizes only a fresh-reset PhysX tournament.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
