#!/usr/bin/env python3
"""Episode-held-out offline gates for visual geometry and action chunks."""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np,torch
from torch.nn import functional as F
from backend.modules.hexcore.object_centric_action_chunk_policy import ObjectChunkPolicy,project_world,unproject_pixels,intersect_horizontal_plane

def batches(indices,batch,rng):
 for start in range(0,len(indices),batch):yield indices[start:start+batch]
def main():
 p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--archive',required=True);p.add_argument('--heldout-receipt');p.add_argument('--heldout-archive');p.add_argument('--recovery-receipt');p.add_argument('--recovery-archive');p.add_argument('--output',required=True);p.add_argument('--weights',required=True);p.add_argument('--epochs',type=int,default=24);p.add_argument('--chunk',type=int,default=16);a=p.parse_args()
 receipt=json.load(open(a.receipt));z=np.load(a.archive);success=np.array(sorted(int(x['episode']) for x in receipt['outcomes'] if x['success']))
 if len(success)<12:raise ValueError('insufficient_episode_authority')
 train_ep,dev_ep=success[:-6],success[-6:]
 episode=z['episode'];step=z['step'];labels=z['privileged_training_target'];actions=z['action'];prop=z['proprioception'];rgb=z['rgb'];recovery_test=None
 if bool(a.recovery_receipt)!=bool(a.recovery_archive):raise ValueError('recovery_authority_pair_required')
 if a.recovery_archive:
  rr=json.load(open(a.recovery_receipt));rz=np.load(a.recovery_archive);re=np.unique(rz['episode']);rtrain,rtest=re[:-6],re[-6:];mask=np.isin(rz['episode'],rtrain);offset=1000
  episode=np.concatenate((episode,rz['episode'][mask]+offset));step=np.concatenate((step,rz['step'][mask]));labels=np.concatenate((labels,rz['privileged_training_target'][mask]));actions=np.concatenate((actions,rz['action'][mask]));prop=np.concatenate((prop,rz['proprioception'][mask]));rgb=np.concatenate((rgb,rz['rgb'][mask]));train_ep=np.concatenate((train_ep,rtrain+offset));recovery_test={k:rz[k][np.isin(rz['episode'],rtest)] for k in ('episode','step','privileged_training_target','action','proprioception','rgb')}
 uv_obj,d_obj=project_world(labels[:,:3]);uv_goal,d_goal=project_world(labels[:,3:6]);uv=np.stack((uv_obj,uv_goal),1);depth=np.stack((d_obj,d_goal),1)
 train_mask=np.isin(episode,train_ep);am,asc=actions[train_mask].mean(0),actions[train_mask].std(0);asc[asc<1e-4]=1
 dm,ds=depth[np.isin(episode,train_ep)].mean(0),depth[np.isin(episode,train_ep)].std(0);ds[ds<1e-4]=1
 def ix(eps):return np.flatnonzero(np.isin(episode,eps)&(step<=250-a.chunk))
 train,dev=ix(train_ep),ix(dev_ep);rng=np.random.default_rng(20260803);torch.manual_seed(20260803);device=torch.device('mps' if torch.backends.mps.is_available() else 'cpu');model=ObjectChunkPolicy(chunk=a.chunk).to(device);opt=torch.optim.AdamW(model.parameters(),3e-4,weight_decay=1e-5)
 def tensors(ind):
  target=np.stack([actions[i:i+a.chunk] for i in ind]);phase=np.stack((np.sin(step[ind]/250*np.pi),np.cos(step[ind]/250*np.pi)),-1).astype(np.float32)
  return [torch.from_numpy(x).to(device) for x in (rgb[ind],prop[ind],phase,uv[ind],(depth[ind]-dm)/ds,(target-am)/asc,(actions[ind]-am)/asc)]
 history=[]
 for epoch in range(a.epochs):
  order=rng.permutation(train);losses=[];model.train()
  for ind in batches(order,96,rng):
   image,pro,phase,tuv,tdepth,tchunk,tstep=tensors(ind);out=model(image,pro,phase)
   geometry=F.smooth_l1_loss(out['uv'],tuv)+4*F.smooth_l1_loss(out['depth'],tdepth)
   chunk=F.smooth_l1_loss(out['chunk'],tchunk);one=F.smooth_l1_loss(out['step'],tstep);loss=.08*geometry+chunk+.25*one
   opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);opt.step();losses.append(float(loss.detach().cpu()))
  history.append(float(np.mean(losses)))
 def evaluate(indices):
  model.eval();P=[]
  with torch.inference_mode():
   for ind in batches(indices,128,rng):
    image,pro,phase,tuv,tdepth,tchunk,tstep=tensors(ind);o=model(image,pro,phase);P.append({k:o[k].cpu().numpy() for k in ('uv','depth','chunk','step')})
  pred={k:np.concatenate([x[k] for x in P]) for k in P[0]};true_uv=uv[indices];true_depth=depth[indices];pd=pred['depth']*ds+dm;world_obj=unproject_pixels(pred['uv'][:,0],pd[:,0]);world_goal=unproject_pixels(pred['uv'][:,1],pd[:,1]);tc=np.stack([actions[i:i+a.chunk] for i in indices]);pc=pred['chunk']*asc+am;ps=pred['step']*asc+am;repeated=np.repeat(ps[:,None],a.chunk,1)
  pre=labels[indices,2]<=.061;plane=intersect_horizontal_plane(pred['uv'][:,0]);plane_error=float(np.linalg.norm(plane[pre]-labels[indices,:3][pre],axis=1).mean()*100) if pre.any() else None
  return {'object_pixel_mae':float(np.linalg.norm(pred['uv'][:,0]-true_uv[:,0],axis=1).mean()),'goal_pixel_mae':float(np.linalg.norm(pred['uv'][:,1]-true_uv[:,1],axis=1).mean()),'object_world_cm_mae':float(np.linalg.norm(world_obj-labels[indices,:3],axis=1).mean()*100),'object_precontact_plane_cm_mae':plane_error,'precontact_fraction':float(pre.mean()),'goal_world_cm_mae':float(np.linalg.norm(world_goal-labels[indices,3:6],axis=1).mean()*100),'chunk_action_mae':float(np.abs(pc-tc).mean()),'repeated_one_step_mae':float(np.abs(repeated-tc).mean()),'chunk_improvement':float(1-np.abs(pc-tc).mean()/np.abs(repeated-tc).mean()),'chunk_temporal_std_ratio':float(pc.std(1).mean()/(tc.std(1).mean()+1e-8))}
 dev_result=evaluate(dev)
 if bool(a.heldout_receipt)!=bool(a.heldout_archive):raise ValueError('heldout_authority_pair_required')
 if recovery_test is not None:
  h_episode=recovery_test['episode'];h_step=recovery_test['step'];h_labels=recovery_test['privileged_training_target'];h_actions=recovery_test['action'];h_prop=recovery_test['proprioception'];h_rgb=recovery_test['rgb'];test_ep=np.unique(h_episode)
  h_uv_obj,h_d_obj=project_world(h_labels[:,:3]);h_uv_goal,h_d_goal=project_world(h_labels[:,3:6]);h_uv=np.stack((h_uv_obj,h_uv_goal),1);h_depth=np.stack((h_d_obj,h_d_goal),1);test=np.flatnonzero(h_step<=250-a.chunk)
  old=(episode,step,labels,actions,prop,rgb,uv,depth);episode,step,labels,actions,prop,rgb,uv,depth=h_episode,h_step,h_labels,h_actions,h_prop,h_rgb,h_uv,h_depth
  test_result=evaluate(test);episode,step,labels,actions,prop,rgb,uv,depth=old;heldout_kind='reserved_student_visited_recovery_episodes'
 elif a.heldout_archive:
  hr=json.load(open(a.heldout_receipt));hz=np.load(a.heldout_archive);h_episode=hz['episode'];h_step=hz['step'];h_labels=hz['privileged_training_target'];h_actions=hz['action'];h_prop=hz['proprioception'];h_rgb=hz['rgb'];test_ep=np.unique(h_episode)
  h_uv_obj,h_d_obj=project_world(h_labels[:,:3]);h_uv_goal,h_d_goal=project_world(h_labels[:,3:6]);h_uv=np.stack((h_uv_obj,h_uv_goal),1);h_depth=np.stack((h_d_obj,h_d_goal),1);test=np.flatnonzero(h_step<=250-a.chunk)
  old=(episode,step,labels,actions,prop,rgb,uv,depth);episode,step,labels,actions,prop,rgb,uv,depth=h_episode,h_step,h_labels,h_actions,h_prop,h_rgb,h_uv,h_depth
  test_result=evaluate(test);episode,step,labels,actions,prop,rgb,uv,depth=old
  heldout_kind='source_disjoint_student_visited_dagger_states'
 else:
  test_ep=dev_ep;test_result=dev_result;heldout_kind='development_reuse_no_sealed_authority'
 gate_a=test_result['object_pixel_mae']<=5 and test_result['object_precontact_plane_cm_mae'] is not None and test_result['object_precontact_plane_cm_mae']<=3;gate_b=test_result['chunk_improvement']>=.20 and test_result['chunk_action_mae']<=.35 and test_result['chunk_temporal_std_ratio']>=.35
 weights=Path(a.weights);weights.parent.mkdir(parents=True,exist_ok=True);torch.save(model.cpu().state_dict(),weights);result={'schema_version':'aion.offline_object_chunk_gate.v1','episode_split':{'train':train_ep.tolist(),'development':dev_ep.tolist(),'sealed_test':test_ep.tolist(),'sealed_kind':heldout_kind},'samples':{'train':len(train),'development':len(dev),'sealed_test':len(test)},'geometry_gate':{'passed':gate_a,'requirement':'object <=5 px and pre-contact table-plane position <=3 cm; exact hidden goal reported separately','sealed':test_result},'action_chunk_gate':{'passed':gate_b,'chunk_length':a.chunk,'requirement':'>=20% ADE improvement, <=0.35 MAE, >=0.35 temporal variation ratio','sealed':test_result},'development':dev_result,'training':{'epochs':a.epochs,'final_loss':history[-1],'minimum_loss':min(history)},'weights_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'runtime_contract':{'visual_inputs':['rgb','bounded_proprioception','mission_lift_cube'],'hidden_simulator_goal_input':False},'physx_authorized':bool(gate_a and gate_b),'claim_boundary':'Offline held-out gates authorize a PhysX challenger, not manipulation competence.'};Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
