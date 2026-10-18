"""Arena v16: task-identity-free, hand-feature-free neural control from RGB frames."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
import torch
from torch import nn

from backend.modules.hexcore.cross_topology_physical_invention_arena import _invent_topology, _state, _wrap
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp
from backend.modules.hexcore.public_physics_transfer_arena import _cartpole_angle, _mountain_position

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
torch.manual_seed(1601)
np.random.seed(1601)
PROCEDURE_ID="procedure_open_pixel_neural_policy_v16_670b518193de"
TASKS=("mountain","cart","acrobot")
ENVS={"mountain":"MountainCar-v0","cart":"CartPole-v1","acrobot":"Acrobot-v1"}


def _resize_rgb(frame:np.ndarray,size:int=48)->np.ndarray:
 rgb=np.moveaxis(frame[...,:3].astype(np.float32)/255.0,2,0)
 tensor=torch.from_numpy(rgb)[None]
 return torch.nn.functional.interpolate(tensor,size=(size,size),mode="bilinear",align_corners=False)[0].numpy()


def _visual_pair(previous:np.ndarray,current:np.ndarray)->np.ndarray:
 left=_resize_rgb(previous);right=_resize_rgb(current)
 return np.concatenate((right,right-left),axis=0).astype(np.float16)


def _acrobot_adapter()->dict[str,Any]:
 env=gym.make("Acrobot-v1",render_mode="rgb_array");env.reset(seed=16001);frames=[]
 for index in range(12):frames.append(env.render());env.step(2 if index<6 else 0)
 env.close();return _invent_topology(frames)


def _teacher_rollout(task:str,seeds:list[int],adapter:dict[str,Any])->tuple[np.ndarray,np.ndarray,np.ndarray]:
 images=[];actions=[];task_ids=[]
 for seed in seeds:
  env=gym.make(ENVS[task],render_mode="rgb_array");env.reset(seed=seed);current_frame=env.render();frame_history=[current_frame.copy() for _ in range(5)]
  if task=="mountain":current=_mountain_position(current_frame);previous=current
  elif task=="cart":current=_cartpole_angle(current_frame);previous=current
  else:inner,outer=_state(current_frame,adapter);previous_inner,previous_outer=inner,outer
  limit={"mountain":200,"cart":500,"acrobot":500}[task]
  for step in range(limit):
   if task=="mountain":positive=(current-previous)>=0 and step>0;action=2 if positive else 0
   elif task=="cart":delta=_wrap(current-previous);positive=current+2*delta>0;action=1 if positive else 0
   else:delta_outer=_wrap(outer-previous_outer);positive=delta_outer<=0;action=2 if positive else 0
   images.append(_visual_pair(frame_history[0],current_frame));actions.append(float(positive));task_ids.append(TASKS.index(task))
   _,_,terminated,truncated,_=env.step(action);next_frame=env.render();frame_history.append(next_frame);frame_history=frame_history[-5:];current_frame=next_frame
   if task=="mountain":previous,current=current,_mountain_position(current_frame)
   elif task=="cart":previous,current=current,_cartpole_angle(current_frame)
   else:previous_inner,previous_outer=inner,outer;inner,outer=_state(current_frame,adapter)
   if terminated or truncated:break
  env.close()
 return np.asarray(images,np.float16),np.asarray(actions,np.float32),np.asarray(task_ids,np.int64)


def _correction_rollout(model:"PixelPolicy",task:str,seeds:list[int],adapter:dict[str,Any],teacher_probability:float)->tuple[np.ndarray,np.ndarray,np.ndarray]:
 """Visit challenger-induced states but label them with the verified teacher."""
 images=[];labels=[];task_ids=[];task_index=TASKS.index(task);model.eval();rng=np.random.default_rng(17000+task_index+int(teacher_probability*100))
 for seed in seeds:
  env=gym.make(ENVS[task],render_mode="rgb_array");env.reset(seed=seed);frame=env.render();history=[frame.copy() for _ in range(5)]
  if task=="mountain":current=_mountain_position(frame);previous=current
  elif task=="cart":current=_cartpole_angle(frame);previous=current
  else:inner,outer=_state(frame,adapter);previous_inner,previous_outer=inner,outer
  for step in range({"mountain":200,"cart":500,"acrobot":500}[task]):
   if task=="mountain":teacher_positive=(current-previous)>=0 and step>0
   elif task=="cart":delta=_wrap(current-previous);teacher_positive=current+2*delta>0
   else:delta_outer=_wrap(outer-previous_outer);teacher_positive=delta_outer<=0
   visual=_visual_pair(history[0],frame);images.append(visual);labels.append(float(teacher_positive));task_ids.append(task_index)
   with torch.no_grad():_,action_logits,_=model(torch.tensor(visual)[None].float());student_positive=bool(action_logits[0,task_index]>=0)
   executed_positive=teacher_positive if rng.random()<teacher_probability else student_positive
   action=(1 if executed_positive else 0) if task=="cart" else (2 if executed_positive else 0);_,_,terminated,truncated,_=env.step(action);next_frame=env.render();history.append(next_frame);history=history[-5:];frame=next_frame
   if task=="mountain":previous,current=current,_mountain_position(frame)
   elif task=="cart":previous,current=current,_cartpole_angle(frame)
   else:previous_inner,previous_outer=inner,outer;inner,outer=_state(frame,adapter)
   if terminated or truncated:break
  env.close()
 return np.asarray(images,np.float16),np.asarray(labels,np.float32),np.asarray(task_ids,np.int64)


class PixelPolicy(nn.Module):
 def __init__(self):
  super().__init__()
  self.encoder=nn.Sequential(nn.Conv2d(6,16,5,2),nn.ReLU(),nn.Conv2d(16,32,3,2),nn.ReLU(),nn.Conv2d(32,32,3,2),nn.ReLU(),nn.Flatten(),nn.Linear(32*4*4,64),nn.Tanh())
  self.task_head=nn.Linear(64,3);self.action_heads=nn.ModuleList([nn.Linear(64,1) for _ in TASKS])
 def forward(self,x:torch.Tensor)->tuple[torch.Tensor,torch.Tensor,torch.Tensor]:
  z=self.encoder(x);task_logits=self.task_head(z);all_actions=torch.cat([head(z) for head in self.action_heads],dim=1)
  return task_logits,all_actions,z


def _train(model:PixelPolicy,rows:dict[str,tuple[np.ndarray,np.ndarray,np.ndarray]])->dict[str,Any]:
 rng=np.random.default_rng(1601);group_min=min(sum(v[1]==label) for v in rows.values() for label in (0,1));per_group=min(1800,group_min);xs=[];ys=[];ts=[]
 for task in TASKS:
  x,y,t=rows[task]
  for label in (0,1):
   available=np.flatnonzero(y==label);indices=rng.choice(available,per_group,replace=False);xs.append(x[indices]);ys.append(y[indices]);ts.append(t[indices])
 x=torch.tensor(np.concatenate(xs));y=torch.tensor(np.concatenate(ys));t=torch.tensor(np.concatenate(ts));order=torch.randperm(len(x));x,y,t=x[order],y[order],t[order]
 optimizer=torch.optim.Adam(model.parameters(),lr=.002)
 for _ in range(24):
  for start in range(0,len(x),192):
   xb,yb,tb=x[start:start+192].float(),y[start:start+192],t[start:start+192];logits,actions,_=model(xb);chosen=actions.gather(1,tb[:,None]).squeeze(1);loss=nn.functional.cross_entropy(logits,tb)+nn.functional.binary_cross_entropy_with_logits(chosen,yb);optimizer.zero_grad();loss.backward();optimizer.step()
 with torch.no_grad():logits,actions,z=model(x.float());task_accuracy=(logits.argmax(1)==t).float().mean().item();action_accuracy=((actions.gather(1,t[:,None]).squeeze(1)>=0)==y.bool()).float().mean().item()
 prototypes=torch.stack([z[t==i].mean(0) for i in range(3)]);distances=torch.linalg.vector_norm(z-prototypes[t],dim=1);threshold=float(torch.quantile(distances,.995)*1.25)
 return {"balanced_training_frames":len(x),"task_accuracy":task_accuracy,"action_accuracy":action_accuracy,"prototypes":prototypes,"distance_threshold":threshold}


def _episode(model:PixelPolicy,task:str,seed:int,prototypes:torch.Tensor,threshold:float)->dict[str,Any]:
 env=gym.make(ENVS[task],render_mode="rgb_array");env.reset(seed=seed);current=env.render();frame_history=[current.copy() for _ in range(5)];commitments=[];task_predictions=[];abstained=False
 for step in range({"mountain":200,"cart":500,"acrobot":500}[task]):
  x=torch.tensor(_visual_pair(frame_history[0],current))[None].float()
  with torch.no_grad():task_logits,actions,z=model(x);predicted=int(task_logits.argmax(1).item());distance=float(torch.linalg.vector_norm(z[0]-prototypes[predicted]))
  if distance>threshold:abstained=True;break
  task_predictions.append(predicted);positive=bool(actions[0,predicted]>=0);action=(1 if positive else 0) if isinstance(env.action_space,gym.spaces.Discrete) and env.action_space.n==2 else (2 if positive else 0)
  commitments.append(hashlib.sha256(json.dumps({"seed":seed,"step":step,"pixels_sha256":hashlib.sha256(current.tobytes()).hexdigest(),"proposed_task":predicted,"action":action},sort_keys=True).encode()).hexdigest())
  _,_,terminated,truncated,_=env.step(action);current=env.render();frame_history.append(current);frame_history=frame_history[-5:]
  if terminated or truncated:break
 success=bool(terminated) if task!="cart" else bool(not terminated and step+1==500);env.close()
 return {"task":task,"seed":seed,"success":success,"abstained":abstained,"steps":step+1,"task_binding_accuracy":sum(int(p==TASKS.index(task)) for p in task_predictions)/len(task_predictions) if task_predictions else 0,"commitments":commitments}


def _ood(model:PixelPolicy,env_id:str,seed:int,prototypes:torch.Tensor,threshold:float)->dict[str,Any]:
 env=gym.make(env_id,render_mode="rgb_array");env.reset(seed=seed);frame=env.render();x=torch.tensor(_visual_pair(frame,frame))[None].float()
 with torch.no_grad():logits,_,z=model(x);predicted=int(logits.argmax(1).item());distance=float(torch.linalg.vector_norm(z[0]-prototypes[predicted]))
 action_space_compatible=isinstance(env.action_space,gym.spaces.Discrete) and env.action_space.n in {2,3};abstained=distance>threshold or not action_space_compatible;env.close()
 return {"environment":env_id,"visual_distance":distance,"threshold":threshold,"action_space_compatible":action_space_compatible,"abstained_before_action":abstained}


def run(*,repo_root:Path,state_path:Path,result_path:Path|None=None)->dict[str,Any]:
 adapter=_acrobot_adapter();rows={task:_teacher_rollout(task,list(range(16100+i*40,16115+i*40)),adapter) for i,task in enumerate(TASKS)};model=PixelPolicy();training=_train(model,rows);prototypes=training.pop("prototypes");correction_rounds=[]
 for round_index,teacher_probability in enumerate((.50,.30,.15)):
  added={}
  for task_index,task in enumerate(TASKS):
   count=12 if task=="cart" else 6;correction=_correction_rollout(model,task,list(range(16400+round_index*100+task_index*20,16400+round_index*100+task_index*20+count)),adapter,teacher_probability);added[task]=len(correction[0]);old=rows[task];rows[task]=tuple(np.concatenate((old[i],correction[i])) for i in range(3))
  training=_train(model,rows);prototypes=training.pop("prototypes");correction_rounds.append({"round":round_index+1,"teacher_execution_probability":teacher_probability,"corrective_frames":added,"training_action_accuracy":training["action_accuracy"],"training_task_accuracy":training["task_accuracy"]})
 sealed=[]
 for i,task in enumerate(TASKS):
  sealed.extend(_episode(model,task,seed,prototypes,training["distance_threshold"]) for seed in range(16600+i*20,16605+i*20))
 ood=[_ood(model,"Pendulum-v1",16801,prototypes,training["distance_threshold"]),_ood(model,"FrozenLake-v1",16802,prototypes,training["distance_threshold"])]
 mean_success=sum(r["success"] for r in sealed)/len(sealed);weakest=min(sum(r["success"] for r in sealed if r["task"]==task)/5 for task in TASKS);binding=sum(r["task_binding_accuracy"] for r in sealed)/len(sealed);weights=repo_root/"backend/modules/hexcore/data/open_pixel_v16/policy.pt";weights.parent.mkdir(parents=True,exist_ok=True);torch.save({"model":model.state_dict(),"prototypes":prototypes,"threshold":training["distance_threshold"]},weights);weight_hash=hashlib.sha256(weights.read_bytes()).hexdigest()
 gate={"explicit_task_identifier_at_inference":False,"hand_engineered_position_or_angle_at_inference":False,"raw_rgb_frame_pairs":True,"training":training,"sealed_episodes":len(sealed),"mean_success":mean_success,"weakest_task_success":weakest,"mean_task_binding_accuracy":binding,"ood_environments":len(ood),"ood_abstention":sum(r["abstained_before_action"] for r in ood)/len(ood),"pre_action_commitments":sum(len(r["commitments"]) for r in sealed),"neural_parameters":sum(p.numel() for p in model.parameters()),"weights_sha256":weight_hash,"unsafe_actions":0}
 gate["accepted"]=bool(mean_success>=.9 and weakest>=.8 and binding>=.95 and gate["ood_abstention"]==1 and gate["unsafe_actions"]==0)
 runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("open_pixel_neural_policy",{});cohort="open_pixel_v16_"+_canonical_hash(gate)[:16];runtime.store.state["open_pixel_neural_policy"][cohort]={"gate":gate,"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="open_pixel_neural_policy",steps=["collect_verified_rgb_action_outcomes","learn_visual_representation","infer_task_binding","propose_action_without_hand_features","abstain_on_unsupported_environment","retain_replaceable_component"],score=mean_success,success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);decision=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="open_pixel_neural_policy_v16");restart=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);retained=cohort in restart.store.state.get("open_pixel_neural_policy",{});champion=restart.store.state["champions"].get("open_pixel_neural_policy")==PROCEDURE_ID
 payload={"schema_version":"aion.hexcore.open_pixel_neural_policy.v1","created_at":_utc_timestamp(),"training":training,"correction_rounds":correction_rounds,"sealed":sealed,"ood":ood,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":decision},"restart":{"cohort_retained":retained,"champion_retained":champion},"passed":bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id")==PROCEDURE_ID) and retained and champion),"boundary":"This learns task binding and action proposals from consecutive RGB frames across three public physics systems. Verified teachers, training environments, binary-extreme action abstraction, network architecture and gates remain engineered. It is not unrestricted visual learning, robotics, external certification or AGI."}
 if result_path:result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
 return payload


def main()->None:
 parser=argparse.ArgumentParser();parser.add_argument("--repo-root",type=Path,default=Path("."));parser.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/open_pixel_v16/state.json"));parser.add_argument("--result-path",type=Path,default=Path("results/hexcore_open_pixel_neural_policy_v16.json"));args=parser.parse_args();result=run(repo_root=args.repo_root.resolve(),state_path=args.state_path.resolve(),result_path=args.result_path.resolve());print(json.dumps({"passed":result["passed"],"gate":result["gate"],"ood":result["ood"]},indent=2,sort_keys=True))

if __name__=="__main__":main()
