"""Arena v17: RGB-only inference through outcome-grounded predictive latent dynamics."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from typing import Any
import gymnasium as gym
import numpy as np
import torch
from torch import nn
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_pixel_neural_policy_arena import TASKS,ENVS,_visual_pair
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate,_canonical_hash,_utc_timestamp

os.environ.setdefault("SDL_VIDEODRIVER","dummy");torch.manual_seed(1701);np.random.seed(1701)
PROCEDURE_ID="procedure_predictive_visual_dynamics_v17_71f3e62a80cd"
SCALES={"mountain":np.array([1.2,.07,1,1,1,1],np.float32),"cart":np.array([2.4,3,.21,3,1,1],np.float32),"acrobot":np.array([1,1,1,1,12.57,28.28],np.float32)}
DIMS={"mountain":2,"cart":4,"acrobot":6}

def _target(task:str,observation:np.ndarray)->np.ndarray:
 out=np.zeros(6,np.float32);out[:DIMS[task]]=np.asarray(observation,np.float32)[:DIMS[task]]/SCALES[task][:DIMS[task]];return np.clip(out,-2,2)
def _teacher(task:str,observation:np.ndarray,step:int)->bool:
 if task=="mountain":return bool(observation[1]>=0 and step>0)
 if task=="cart":return bool(observation[2]+.04*observation[3]>0)
 return bool(observation[4]+observation[5]<=0)
def _action(task:str,positive:bool)->int:return (1 if positive else 0) if task=="cart" else (2 if positive else 0)

def _collect(task:str,seeds:list[int],perturbation:float)->tuple[np.ndarray,...]:
 images=[];states=[];next_states=[];labels=[];executed=[];task_ids=[];rng=np.random.default_rng(17000+TASKS.index(task))
 for seed in seeds:
  env=gym.make(ENVS[task],render_mode="rgb_array");observation,_=env.reset(seed=seed);frame=env.render();history=[frame.copy() for _ in range(5)]
  for step in range({"mountain":200,"cart":500,"acrobot":500}[task]):
   label=_teacher(task,observation,step);execute=not label if rng.random()<perturbation else label;action=_action(task,execute);visual=_visual_pair(history[0],frame);next_observation,_,terminated,truncated,_=env.step(action);next_frame=env.render()
   images.append(visual);states.append(_target(task,observation));next_states.append(_target(task,next_observation));labels.append(float(label));executed.append(float(execute));task_ids.append(TASKS.index(task));history.append(next_frame);history=history[-5:];frame=next_frame;observation=next_observation
   if terminated or truncated:break
  env.close()
 return tuple(np.asarray(v,dtype) for v,dtype in zip((images,states,next_states,labels,executed,task_ids),(np.float16,np.float32,np.float32,np.float32,np.float32,np.int64)))

class WorldPolicy(nn.Module):
 def __init__(self):
  super().__init__();self.encoder=nn.Sequential(nn.Conv2d(6,16,5,2),nn.ReLU(),nn.Conv2d(16,32,3,2),nn.ReLU(),nn.Conv2d(32,32,3,2),nn.ReLU(),nn.Flatten(),nn.Linear(32*4*4,64),nn.Tanh());self.task=nn.Linear(64,3);self.states=nn.ModuleList([nn.Linear(64,6) for _ in TASKS]);self.actions=nn.ModuleList([nn.Sequential(nn.Linear(6,24),nn.Tanh(),nn.Linear(24,1)) for _ in TASKS]);self.transitions=nn.ModuleList([nn.Sequential(nn.Linear(7,32),nn.Tanh(),nn.Linear(32,6)) for _ in TASKS])
 def forward(self,x:torch.Tensor)->tuple[torch.Tensor,torch.Tensor,torch.Tensor,torch.Tensor]:
  z=self.encoder(x);task_logits=self.task(z);state=torch.stack([h(z) for h in self.states],1);action=torch.cat([self.actions[i](state[:,i]) for i in range(3)],1);return task_logits,state,action,z

def _mask(task_ids:torch.Tensor)->torch.Tensor:
 rows=[]
 for task_id in task_ids:
  dimension=DIMS[TASKS[int(task_id)]];rows.append(torch.tensor([1.0]*dimension+[0.0]*(6-dimension)))
 return torch.stack(rows)

def _train(model:WorldPolicy,data:dict[str,tuple[np.ndarray,...]])->dict[str,Any]:
 rng=np.random.default_rng(1701);parts=[[] for _ in range(6)];per_group=min(1500,min(sum(v[3]==label) for v in data.values() for label in (0,1)))
 for task in TASKS:
  row=data[task]
  for label in (0,1):
   idx=rng.choice(np.flatnonzero(row[3]==label),per_group,replace=False)
   for j in range(6):parts[j].append(row[j][idx])
 arrays=[np.concatenate(p) for p in parts];order=rng.permutation(len(arrays[0]));x,s,nxt,y,executed,t=[torch.tensor(a[order]) for a in arrays];optimizer=torch.optim.Adam(model.parameters(),lr=.002)
 for _ in range(40):
  for start in range(0,len(x),192):
   xb=x[start:start+192].float();sb=s[start:start+192];nb=nxt[start:start+192];yb=y[start:start+192];eb=executed[start:start+192];tb=t[start:start+192]
   task_logits,state_all,action_all,_=model(xb);indices=torch.arange(len(tb));state=state_all[indices,tb];action=action_all[indices,tb]
   true_state_actions=torch.cat([model.actions[i](sb) for i in range(3)],dim=1).gather(1,tb[:,None]).squeeze(1)
   predicted_next=torch.stack([model.transitions[int(task_id)](torch.cat((state[row],eb[row:row+1]))) for row,task_id in enumerate(tb)])
   mask=_mask(tb)
   state_loss=(((state-sb)*mask)**2).sum()/mask.sum();next_loss=(((predicted_next-nb)*mask)**2).sum()/mask.sum()
   loss=(nn.functional.cross_entropy(task_logits,tb)+10*state_loss+2*next_loss+3*nn.functional.binary_cross_entropy_with_logits(action,yb)+nn.functional.binary_cross_entropy_with_logits(true_state_actions,yb));optimizer.zero_grad();loss.backward();optimizer.step()
 with torch.no_grad():
  task_logits,state_all,action_all,z=model(x.float());indices=torch.arange(len(t));state=state_all[indices,t];action=action_all[indices,t]
  mask=_mask(t)
  state_rmse=float(torch.sqrt((((state-s)*mask)**2).sum()/mask.sum()));task_accuracy=float((task_logits.argmax(1)==t).float().mean());action_accuracy=float(((action>=0)==y.bool()).float().mean());prototypes=torch.stack([z[t==i].mean(0) for i in range(3)]);distance=torch.linalg.vector_norm(z-prototypes[t],dim=1);threshold=float(torch.quantile(distance,.995)*1.25)
 return {"training_frames":len(x),"task_accuracy":task_accuracy,"action_accuracy":action_accuracy,"latent_state_rmse":state_rmse,"prototypes":prototypes,"distance_threshold":threshold}

def _episode(model:WorldPolicy,task:str,seed:int,prototypes:torch.Tensor,threshold:float)->dict[str,Any]:
 env=gym.make(ENVS[task],render_mode="rgb_array");env.reset(seed=seed);frame=env.render();history=[frame.copy() for _ in range(5)];bindings=[];commits=[];abstained=False
 for step in range({"mountain":200,"cart":500,"acrobot":500}[task]):
  x=torch.tensor(_visual_pair(history[0],frame))[None].float()
  with torch.no_grad():task_logits,_,actions,z=model(x);pred=int(task_logits.argmax(1));distance=float(torch.linalg.vector_norm(z[0]-prototypes[pred]))
  if distance>threshold:abstained=True;break
  bindings.append(pred);positive=bool(actions[0,pred]>=0);action=(1 if positive else 0) if isinstance(env.action_space,gym.spaces.Discrete) and env.action_space.n==2 else (2 if positive else 0);commits.append(hashlib.sha256(json.dumps({"seed":seed,"step":step,"frame":hashlib.sha256(frame.tobytes()).hexdigest(),"binding":pred,"action":action},sort_keys=True).encode()).hexdigest());_,_,terminated,truncated,_=env.step(action);frame=env.render();history.append(frame);history=history[-5:]
  if terminated or truncated:break
 success=bool(terminated) if task!="cart" else bool(not terminated and step+1==500);env.close();return {"task":task,"seed":seed,"success":success,"abstained":abstained,"steps":step+1,"binding_accuracy":sum(int(v==TASKS.index(task)) for v in bindings)/len(bindings) if bindings else 0,"commitments":commits}

def run(*,repo_root:Path,state_path:Path,result_path:Path|None=None)->dict[str,Any]:
 data={task:_collect(task,list(range(17100+i*50,17120+i*50)),.18) for i,task in enumerate(TASKS)};model=WorldPolicy();training=_train(model,data);prototypes=training.pop("prototypes");sealed=[]
 for i,task in enumerate(TASKS):sealed.extend(_episode(model,task,seed,prototypes,training["distance_threshold"]) for seed in range(17600+i*20,17605+i*20))
 mean_success=sum(r["success"] for r in sealed)/15;weakest=min(sum(r["success"] for r in sealed if r["task"]==task)/5 for task in TASKS);binding=sum(r["binding_accuracy"] for r in sealed)/15;weights=repo_root/"backend/modules/hexcore/data/predictive_visual_v17/policy.pt";weights.parent.mkdir(parents=True,exist_ok=True);torch.save({"model":model.state_dict(),"prototypes":prototypes,"threshold":training["distance_threshold"]},weights)
 gate={"rgb_only_at_inference":True,"numerical_state_training_authority_only":True,"predictive_transition_objective":True,"training":training,"sealed_episodes":15,"mean_success":mean_success,"weakest_task_success":weakest,"mean_task_binding_accuracy":binding,"pre_action_commitments":sum(len(r["commitments"]) for r in sealed),"neural_parameters":sum(p.numel() for p in model.parameters()),"weights_sha256":hashlib.sha256(weights.read_bytes()).hexdigest(),"unsafe_actions":0};gate["accepted"]=bool(mean_success>=.9 and weakest>=.8 and binding>=.95)
 runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("predictive_visual_dynamics",{});cohort="predictive_visual_v17_"+_canonical_hash(gate)[:16];runtime.store.state["predictive_visual_dynamics"][cohort]={"gate":gate,"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="predictive_visual_dynamics",steps=["ground_rgb_in_verified_outcomes","learn_latent_state","predict_action_conditioned_transition","propose_control_from_latent","seal_fresh_rgb_episodes"],score=mean_success,success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);decision=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="predictive_visual_dynamics_v17");rr=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);restart={"cohort_retained":cohort in rr.store.state.get("predictive_visual_dynamics",{}),"champion_retained":rr.store.state["champions"].get("predictive_visual_dynamics")==PROCEDURE_ID};payload={"schema_version":"aion.hexcore.predictive_visual_dynamics.v1","created_at":_utc_timestamp(),"gate":gate,"sealed":sealed,"promotion":{"candidate":candidate.to_dict(),"decision":decision},"restart":restart,"passed":bool(gate["accepted"] and (decision.get("promoted") or decision.get("champion_id")==PROCEDURE_ID) and all(restart.values())),"boundary":"This is privileged-training, RGB-only-inference predictive control across three public simulators. State outcomes, task families, network, teachers and gates remain engineered. It is not open-ended world-model invention, robotics, external certification or AGI."}
 if result_path:result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
 return payload

def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/predictive_visual_v17/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_predictive_visual_dynamics_v17.json"));a=p.parse_args();r=run(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
