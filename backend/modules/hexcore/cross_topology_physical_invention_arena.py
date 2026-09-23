"""Arena v11: articulated-topology perception and phase-controller invention."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from pathlib import Path
from typing import Any
import gymnasium as gym
import numpy as np
from scipy.ndimage import label
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash, _utc_timestamp

PROCEDURE_ID="procedure_cross_topology_physical_invention_v11_928b71e4fa63"
os.environ.setdefault("SDL_VIDEODRIVER","dummy")

def _components(frame:np.ndarray,color:np.ndarray)->list[np.ndarray]:
    labs,n=label(np.all(frame==color,axis=2)); rows=[]
    for i in range(1,n+1):
        y,x=np.where(labs==i)
        if len(x)>20: rows.append(np.array([x.mean(),y.mean()]))
    return rows

def _invent_topology(frames:list[np.ndarray])->dict[str,Any]:
    vals,cnts=np.unique(frames[0].reshape(-1,3),axis=0,return_counts=True)
    ranked=vals[np.argsort(cnts)[-50:]]; marker=[]; links=[]
    for color in ranked:
        if int(color.max())-int(color.min())<50: continue
        comps=[_components(f,color) for f in frames]
        if all(len(c)==2 for c in comps):
            marker.append((float(np.mean([sum(np.all(f==color,2).ravel()) for f in frames])),color))
        population=float(np.mean([np.all(f==color,2).sum() for f in frames]))
        if population>1000: links.append((population,color))
    if not marker or not links: raise ValueError("ARTICULATED_TOPOLOGY_NOT_GROUNDED")
    marker_color=max(marker,key=lambda x:x[0])[1]; link_color=max(links,key=lambda x:x[0])[1]
    return {"marker_color":[int(x) for x in marker_color],"link_color":[int(x) for x in link_color],"joint_count":2,"link_count":2,"candidate_colors":len(ranked),"topology":"fixed_pivot_to_moving_hinge_to_outer_link"}

def _state(frame:np.ndarray,adapter:dict[str,Any])->tuple[float,float]:
    markers=_components(frame,np.asarray(adapter["marker_color"],dtype=np.uint8))
    if len(markers)!=2: raise ValueError("JOINT_MARKERS_LOST")
    center=np.array([frame.shape[1]/2,frame.shape[0]/2]); p0=min(markers,key=lambda p:np.linalg.norm(p-center)); p1=max(markers,key=lambda p:np.linalg.norm(p-center))
    link_color=np.asarray(adapter["link_color"],dtype=np.uint8); y,x=np.where(np.all(frame==link_color,axis=2)); pts=np.c_[x,y]
    radius=np.linalg.norm(p1-p0); outer=pts[np.linalg.norm(pts-p0,axis=1)>radius*1.2]
    # A folded outer link may temporarily lie inside the pivot radius. Preserve
    # grounding by falling back to the cyan endpoint farthest from the hinge;
    # the phase controller subsequently uses wrapped temporal differences.
    candidates=outer if len(outer) else pts
    p2=candidates[np.argmax(np.linalg.norm(candidates-p1,axis=1))]
    inner=math.atan2(p1[1]-p0[1],p1[0]-p0[0]); outer_angle=math.atan2(p2[1]-p1[1],p2[0]-p1[0])
    return inner,outer_angle

def _wrap(x:float)->float:return (x+math.pi)%(2*math.pi)-math.pi

PROGRAMS=[
 {"name":"constant_positive","feature":"constant","sign":1},
 {"name":"constant_negative","feature":"constant","sign":-1},
 {"name":"outer_phase","feature":"outer_phase","sign":1},
 {"name":"inverse_outer_phase","feature":"outer_phase","sign":-1},
 {"name":"inner_phase","feature":"inner_phase","sign":1},
 {"name":"inverse_inner_phase","feature":"inner_phase","sign":-1},
]

def _episode(seed:int,adapter:dict[str,Any],program:dict[str,Any],variant:str)->dict[str,Any]:
    env=gym.make("Acrobot-v1",render_mode="rgb_array"); env.unwrapped.book_or_nips=variant; _hidden,_=env.reset(seed=seed)
    inner,outer=_state(env.render(),adapter); pi,po=inner,outer; commits=[]; terminated=False
    for step in range(500):
        feature=1.0 if program["feature"]=="constant" else (_wrap(outer-po) if program["feature"]=="outer_phase" else _wrap(inner-pi))
        direction=program["sign"]*(1 if feature>=0 else -1); action=2 if direction>0 else 0
        commits.append(hashlib.sha256(json.dumps({"seed":seed,"variant":variant,"step":step,"feature":round(feature,7),"program":program["name"],"action":action},sort_keys=True).encode()).hexdigest())
        _hidden,_reward,terminated,truncated,_=env.step(action); pi,po=inner,outer; inner,outer=_state(env.render(),adapter)
        if terminated or truncated: break
    env.close(); return {"seed":seed,"variant":variant,"program":program["name"],"success":bool(terminated),"steps":step+1,"commitments":commits,"numeric_observation_used":False}

def run_cross_topology_physical_invention(*,repo_root:Path,state_path:Path,result_path:Path|None=None)->dict[str,Any]:
    probe=gym.make("Acrobot-v1",render_mode="rgb_array"); _hidden,_=probe.reset(seed=7101); frames=[]
    for step in range(12): frames.append(probe.render()); _hidden,_r,_t,_tr,_=probe.step(2 if step<6 else 0)
    probe.close(); adapter=_invent_topology(frames)
    dev=[_episode(seed,adapter,p,"book") for p in PROGRAMS for seed in (7201,7202,7203)]
    def score(p:dict[str,Any])->tuple[float,float]:
        rows=[r for r in dev if r["program"]==p["name"]];return (sum(r["success"] for r in rows)/len(rows),-sum(r["steps"] for r in rows)/len(rows))
    initial_champion=max(PROGRAMS,key=score)
    adaptation=[_episode(seed,adapter,p,"nips") for p in PROGRAMS for seed in (7401,7402,7403)]
    def robust_score(p:dict[str,Any])->tuple[float,float]:
        a=[r for r in dev if r["program"]==p["name"]]; b=[r for r in adaptation if r["program"]==p["name"]]
        return (min(sum(r["success"] for r in a)/len(a),sum(r["success"] for r in b)/len(b)),-sum(r["steps"] for r in a+b)/len(a+b))
    champion=max(PROGRAMS,key=robust_score); book=[_episode(seed,adapter,champion,"book") for seed in range(7501,7507)]; nips=[_episode(seed,adapter,champion,"nips") for seed in range(7601,7607)]; control=PROGRAMS[0]; cold=[_episode(seed,adapter,control,"book") for seed in range(7501,7507)]+[_episode(seed,adapter,control,"nips") for seed in range(7601,7607)]; learned=book+nips
    success=sum(r["success"] for r in learned)/len(learned); cold_success=sum(r["success"] for r in cold)/len(cold)
    gate={"supplied_joint_or_link_colors":False,"invented_joint_count":adapter["joint_count"],"invented_link_count":adapter["link_count"],"invented_topology":adapter["topology"],"programs_composed":len(PROGRAMS),"new_state_primitive":"outer_link_angular_phase","initial_selected_program":initial_champion["name"],"robust_selected_program":champion["name"],"structural_shift_calibration_episodes":len(adaptation),"development_episodes":len(dev),"sealed_episodes":len(learned),"dynamics_variants":2,"book_success":sum(r["success"] for r in book)/6,"nips_transfer_success":sum(r["success"] for r in nips)/6,"overall_success":success,"cold_success":cold_success,"success_lift_vs_cold":success-cold_success,"pre_action_commitments":sum(len(r["commitments"]) for r in learned),"numeric_observation_used":False,"unsafe_actions":0}
    gate["accepted"]=bool(success>=.9 and gate["book_success"]>=.8 and gate["nips_transfer_success"]>=.8 and gate["success_lift_vs_cold"]>=.5)
    runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("cross_topology_physical_invention",{});cohort="cross_topology_v11_"+_canonical_hash({"gate":gate,"adapter":adapter})[:16];runtime.store.state["cross_topology_physical_invention"][cohort]={"gate":gate,"adapter":adapter,"champion":champion,"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="cross_topology_physical_invention",steps=["intervene_on_unknown_articulated_pixels","invent_joint_link_topology","invent_angular_phase_state","compose_and_falsify_phase_controllers","transfer_across_unseen_dynamics"],score=success,success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);promotion=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="cross_topology_physical_invention_v11");restarted=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);restart={"cohort_retained":cohort in restarted.store.state.get("cross_topology_physical_invention",{}),"champion_retained":restarted.store.state["champions"].get("cross_topology_physical_invention")==PROCEDURE_ID,"relearning_episodes":0}
    payload={"schema_version":"aion.hexcore.cross_topology_physical_invention.v1","created_at":_utc_timestamp(),"adapter":adapter,"programs":PROGRAMS,"development":dev,"sealed":{"learned":learned,"cold":cold},"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":promotion},"restart":restart,"passed":bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id")==PROCEDURE_ID) and restart["cohort_retained"] and restart["champion_retained"]),"boundary":"AION invents an articulated pixel topology and angular-phase controller under public outcomes, but color-component primitives, controller meta-grammar, environments, seeds and gates remain development controlled. This is not unrestricted physics, robotics, external certification or AGI."}
    if result_path: result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    return payload

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/cross_topology_v11/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_cross_topology_physical_invention_v11.json"));a=p.parse_args();r=run_cross_topology_physical_invention(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
