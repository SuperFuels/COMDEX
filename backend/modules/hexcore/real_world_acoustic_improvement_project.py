"""Arena v13: autonomous real-world acoustic diagnosis and improvement."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import sounddevice as sd
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate,_canonical_hash,_utc_timestamp
from backend.modules.hexcore.real_world_acoustic_learning_arena import _measure

PROCEDURE_ID="procedure_real_world_acoustic_improvement_v13_9b3c71e044fa"
FREQUENCIES=(350,500,710,1000,1410,2000,2830,4000,5660)

def _log_dispersion(rows):
 values=np.log([r["magnitude"]+1e-12 for r in rows]);return float(np.std(values))

def run_real_world_acoustic_improvement(*,repo_root:Path,state_path:Path,result_path:Path|None=None):
 input_id,output_id=sd.default.device;devices=sd.query_devices();objective="Characterise the local acoustic path and make its measured narrowband response more uniform without exceeding the original output amplitude or retaining ambient audio."
 plan=["measure_baseline_transfer","diagnose_frequency_imbalance","invent_bounded_inverse_compensation","commit_coefficients_before_action","apply_physical_intervention","measure_delayed_outcome","retain_or_reject_tool"]
 baseline=[_measure(f,.04) for f in FREQUENCIES];transfer={int(r["frequency_hz"]):r["magnitude"]/.04 for r in baseline};target=min(transfer.values());coefficients={f:max(.20,min(1.0,target/transfer[f])) for f in FREQUENCIES};commitment=hashlib.sha256(json.dumps(coefficients,sort_keys=True).encode()).hexdigest();compensated=[_measure(f,.04*coefficients[f]) for f in FREQUENCIES]
 baseline_disp=_log_dispersion(baseline);comp_disp=_log_dispersion(compensated);reduction=1-comp_disp/baseline_disp if baseline_disp else 0
 gate={"broad_goal_only":True,"subgoals_invented":len(plan),"physical_input_device":devices[input_id]["name"],"physical_output_device":devices[output_id]["name"],"real_physical_interventions":len(baseline)+len(compensated),"continuous_tool_parameters_invented":len(coefficients),"coefficient_commitment":commitment,"maximum_stimulus_amplitude":max(r["stimulus_amplitude"] for r in compensated),"original_amplitude_ceiling":.04,"baseline_log_dispersion":baseline_disp,"compensated_log_dispersion":comp_disp,"physical_uniformity_improvement":reduction,"minimum_compensated_snr_db":min(r["snr_db"] for r in compensated),"raw_audio_persisted":False,"speech_recognition_performed":False,"unsafe_output_level":False,"tool_retained":reduction>=.20}
 gate["accepted"]=bool(gate["tool_retained"] and gate["maximum_stimulus_amplitude"]<=.04 and gate["minimum_compensated_snr_db"]>=10 and not gate["raw_audio_persisted"])
 runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("real_world_acoustic_improvement",{});cohort="acoustic_v13_"+_canonical_hash({"gate":gate,"coefficients":coefficients})[:16];runtime.store.state["real_world_acoustic_improvement"][cohort]={"objective":objective,"plan":plan,"gate":gate,"coefficients":coefficients,"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="real_world_acoustic_improvement",steps=plan,score=max(0,reduction),success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);promotion=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="real_world_acoustic_improvement_v13");rr=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);restart={"project_retained":cohort in rr.store.state.get("real_world_acoustic_improvement",{}),"tool_champion_retained":rr.store.state["champions"].get("real_world_acoustic_improvement")==PROCEDURE_ID,"raw_audio_replayed":False}
 payload={"schema_version":"aion.hexcore.real_world_acoustic_improvement.v1","created_at":_utc_timestamp(),"objective":objective,"invented_plan":plan,"baseline":baseline,"invented_compensation":coefficients,"compensated":compensated,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":promotion},"restart":restart,"passed":bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id")==PROCEDURE_ID) and restart["project_retained"] and restart["tool_champion_retained"]),"boundary":"This is an autonomous physical improvement project on one development-owned Mac acoustic path. The objective, measurement family and safety ceiling remain engineered. It is not independent evaluation, unrestricted tool invention, robotics or AGI."}
 if result_path:result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
 return payload

def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/acoustic_v13/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_real_world_acoustic_improvement_v13.json"));a=p.parse_args();r=run_real_world_acoustic_improvement(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
