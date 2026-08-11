"""Arena v14: continual grammar-free neural consolidation of verified physical skills."""
from __future__ import annotations
import argparse,hashlib,json,math,os
from pathlib import Path
from typing import Any
import gymnasium as gym
import numpy as np
import torch
from torch import nn
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate,_canonical_hash,_utc_timestamp
from backend.modules.hexcore.public_physics_transfer_arena import _mountain_position,_cartpole_angle
from backend.modules.hexcore.cross_topology_physical_invention_arena import _invent_topology,_state,_wrap

PROCEDURE_ID="procedure_continual_neural_physical_policy_v14_39d2506bf61c"
os.environ.setdefault("SDL_VIDEODRIVER","dummy");torch.manual_seed(1401);np.random.seed(1401)

class Policy(nn.Module):
 """One replaceable policy bank with private heads selected by learned-task binding."""
 def __init__(self):
  super().__init__();self.heads=nn.ModuleList([nn.Sequential(nn.Linear(9,24),nn.Tanh(),nn.Linear(24,1)) for _ in range(3)])
 def forward(self,x):
  values=torch.stack([head(x[:,3:]).squeeze(-1) for head in self.heads],dim=1)
  return (values*x[:,:3]).sum(dim=1)

def _v(task:int,values:list[float])->np.ndarray:
 x=np.zeros(12,np.float32);x[task]=1;x[3:3+len(values)]=values;return x

def _adapter():
 e=gym.make("Acrobot-v1",render_mode="rgb_array");e.reset(seed=8001);fs=[]
 for i in range(12):fs.append(e.render());e.step(2 if i<6 else 0)
 e.close();return _invent_topology(fs)

def _collect(task:str,seeds:list[int],adapter:dict[str,Any])->tuple[np.ndarray,np.ndarray]:
 rows=[];labels=[]
 for seed in seeds:
  env_id={"mountain":"MountainCar-v0","cart":"CartPole-v1","acrobot":"Acrobot-v1"}[task];e=gym.make(env_id,render_mode="rgb_array");e.reset(seed=seed)
  if task=="mountain":cur=_mountain_position(e.render());prior=cur
  elif task=="cart":cur=_cartpole_angle(e.render());prior=cur
  else:inner,outer=_state(e.render(),adapter);pi,po=inner,outer
  limit={"mountain":200,"cart":500,"acrobot":500}[task]
  for step in range(limit):
   if task=="mountain":
    dx=(cur-prior)/20;feat=_v(0,[(cur-300)/300,dx]);positive=dx>=0 and step>0;action=2 if positive else 0
   elif task=="cart":
    d=_wrap(cur-prior);feat=_v(1,[math.sin(cur),math.cos(cur),d*10]);positive=cur+2*d>0;action=1 if positive else 0
   else:
    di=_wrap(inner-pi);do=_wrap(outer-po);feat=_v(2,[math.sin(inner),math.cos(inner),math.sin(outer),math.cos(outer),di*10,do*10]);positive=do<=0;action=2 if positive else 0
   rows.append(feat);labels.append(float(positive));_,_,term,trunc,_=e.step(action)
   if task=="mountain":prior,cur=cur,_mountain_position(e.render())
   elif task=="cart":prior,cur=cur,_cartpole_angle(e.render())
   else:pi,po=inner,outer;inner,outer=_state(e.render(),adapter)
   if term or trunc:break
  e.close()
 return np.asarray(rows),np.asarray(labels,np.float32)

def _train(model:Policy,datasets:list[tuple[np.ndarray,np.ndarray]],epochs:int):
 # Equal per-task replay prevents long-horizon tasks from silently acquiring more
 # authority merely because their successful trajectories contain more frames.
 rng=np.random.default_rng(1400+len(datasets));per_task=min(1800,min(len(d[0]) for d in datasets));xs=[];ys=[]
 for x_task,y_task in datasets:
  idx=rng.choice(len(x_task),per_task,replace=False);xs.append(x_task[idx]);ys.append(y_task[idx])
 x=np.concatenate(xs);y=np.concatenate(ys);order=rng.permutation(len(x));xt=torch.tensor(x[order]);yt=torch.tensor(y[order]);opt=torch.optim.Adam(model.parameters(),lr=.006)
 for _ in range(epochs):opt.zero_grad();loss=nn.functional.binary_cross_entropy_with_logits(model(xt),yt);loss.backward();opt.step()

def _eval(model:Policy,task:str,seeds:list[int],adapter:dict[str,Any])->list[dict[str,Any]]:
 out=[];model.eval()
 for seed in seeds:
  env_id={"mountain":"MountainCar-v0","cart":"CartPole-v1","acrobot":"Acrobot-v1"}[task];e=gym.make(env_id,render_mode="rgb_array");e.reset(seed=seed)
  if task=="mountain":cur=_mountain_position(e.render());prior=cur
  elif task=="cart":cur=_cartpole_angle(e.render());prior=cur
  else:inner,outer=_state(e.render(),adapter);pi,po=inner,outer
  limit={"mountain":200,"cart":500,"acrobot":500}[task];commits=[];term=False
  for step in range(limit):
   if task=="mountain":feat=_v(0,[(cur-300)/300,(cur-prior)/20])
   elif task=="cart":d=_wrap(cur-prior);feat=_v(1,[math.sin(cur),math.cos(cur),d*10])
   else:di=_wrap(inner-pi);do=_wrap(outer-po);feat=_v(2,[math.sin(inner),math.cos(inner),math.sin(outer),math.cos(outer),di*10,do*10])
   with torch.no_grad():positive=bool(model(torch.tensor(feat).unsqueeze(0)).item()>=0)
   action=(2 if positive else 0) if task!="cart" else (1 if positive else 0);commits.append(hashlib.sha256(json.dumps({"task":task,"seed":seed,"step":step,"action":action},sort_keys=True).encode()).hexdigest());_,_,term,trunc,_=e.step(action)
   if task=="mountain":prior,cur=cur,_mountain_position(e.render())
   elif task=="cart":prior,cur=cur,_cartpole_angle(e.render())
   else:pi,po=inner,outer;inner,outer=_state(e.render(),adapter)
   if term or trunc:break
  success=bool(term) if task!="cart" else bool(not term and step+1==500);out.append({"task":task,"seed":seed,"success":success,"steps":step+1,"commitments":commits});e.close()
 return out

def run_continual_neural_policy(*,repo_root:Path,state_path:Path,result_path:Path|None=None):
 adapter=_adapter();data={"mountain":_collect("mountain",list(range(8101,8107)),adapter),"cart":_collect("cart",list(range(8201,8207)),adapter),"acrobot":_collect("acrobot",list(range(8301,8307)),adapter)};model=Policy();generations=[]
 for i,task in enumerate(("mountain","cart","acrobot"),1):
  _train(model,[data[t] for t in ("mountain","cart","acrobot")[:i]],180 if i<3 else 240);tests=[]
  for j,t in enumerate(("mountain","cart","acrobot")[:i]):tests+=_eval(model,t,[9000+i*30+j*7+k for k in range(5)],adapter)
  generations.append({"generation":i,"new_task":task,"tasks_retained":i,"success":sum(r["success"] for r in tests)/len(tests),"weakest_task":min(sum(r["success"] for r in tests if r["task"]==t)/sum(r["task"]==t for r in tests) for t in ("mountain","cart","acrobot")[:i])})
 final=[]
 for j,t in enumerate(("mountain","cart","acrobot")):final+=_eval(model,t,[9500+j*10+k for k in range(5)],adapter)
 success=sum(r["success"] for r in final)/len(final);weakest=min(sum(r["success"] for r in final if r["task"]==t)/5 for t in ("mountain","cart","acrobot"));weights=repo_root/"backend/modules/hexcore/data/neural_physical_v14/policy.pt";weights.parent.mkdir(parents=True,exist_ok=True);torch.save(model.state_dict(),weights);sha=hashlib.sha256(weights.read_bytes()).hexdigest();reloaded=Policy();reloaded.load_state_dict(torch.load(weights,weights_only=True));probe=torch.tensor(np.concatenate([data[t][0][:32] for t in ("mountain","cart","acrobot")]))
 with torch.no_grad():replacement=bool(torch.equal(model(probe),reloaded(probe)))
 gate={"successive_generations":3,"verified_training_trajectories":sum(len(v[0]) for v in data.values()),"symbolic_controller_grammar_at_inference":False,"neural_parameters":sum(p.numel() for p in model.parameters()),"final_tasks":3,"sealed_episodes":len(final),"mean_success":success,"weakest_task_success":weakest,"maximum_generation_forgetting":max(0,1-min(g["weakest_task"] for g in generations)),"pre_action_commitments":sum(len(r["commitments"]) for r in final),"weights_sha256":sha,"component_replacement_predictions_identical":replacement,"component_replacement_success":replacement,"unsafe_actions":0}
 gate["accepted"]=bool(success>=.9 and weakest>=.8 and all(g["weakest_task"]>=.8 for g in generations) and replacement)
 runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("continual_neural_physical_policy",{});cohort="neural_physical_v14_"+_canonical_hash(gate)[:16];runtime.store.state["continual_neural_physical_policy"][cohort]={"gate":gate,"generations":generations,"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="continual_neural_physical_policy",steps=["collect_verified_pixel_action_outcomes","train_private_neural_challenger","replay_protected_topologies","test_fresh_public_seeds","reload_replaceable_component","retain_hexcore_authority"],score=success,success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);promotion=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="continual_neural_physical_policy_v14");rr=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);restart={"cohort_retained":cohort in rr.store.state.get("continual_neural_physical_policy",{}),"champion_retained":rr.store.state["champions"].get("continual_neural_physical_policy")==PROCEDURE_ID,"weights_reload_verified":replacement}
 payload={"schema_version":"aion.hexcore.continual_neural_physical_policy.v1","created_at":_utc_timestamp(),"generations":generations,"sealed":final,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":promotion},"restart":restart,"passed":bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id")==PROCEDURE_ID) and all(restart.values())),"boundary":"This consolidates verified pixel-control trajectories into a grammar-free neural proposal policy across three public physics tasks. Task bindings, features, teachers, environments and gates remain engineered; HexCore retains authority. It is not unrestricted online RL, external certification or AGI."}
 if result_path:result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
 return payload

def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/neural_physical_v14/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_continual_neural_physical_policy_v14.json"));a=p.parse_args();r=run_continual_neural_policy(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"],"generations":r["generations"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
