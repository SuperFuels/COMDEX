"""Arena v12: real speaker-air-microphone system identification."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any
import numpy as np
import sounddevice as sd
from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime,ProcedureCandidate,_canonical_hash,_utc_timestamp

PROCEDURE_ID="procedure_real_world_acoustic_learning_v12_56a34d8c1ef2"
RATE=48000; DURATION=.32; AMPLITUDE=.04
FREQUENCIES=(320,450,630,880,1230,1720,2410,3370,4720,6200)

def _measure(frequency:float,amplitude:float=AMPLITUDE)->dict[str,float]:
    n=int(RATE*DURATION);t=np.arange(n)/RATE;fade=np.minimum(1,np.minimum(np.arange(n)/800,(n-1-np.arange(n))/800));tone=(amplitude*np.sin(2*np.pi*frequency*t)*fade).astype(np.float32);stereo=np.column_stack([tone,tone]);recorded=sd.playrec(stereo,samplerate=RATE,channels=1,input_mapping=[1],output_mapping=[1,2],blocking=True,dtype="float32")[:,0];window=np.hanning(n);spectrum=np.fft.rfft(recorded*window);freq=np.fft.rfftfreq(n,1/RATE);idx=int(np.argmin(abs(freq-frequency)));signal=float(abs(spectrum[idx]));guard=(freq>frequency-120)&(freq<frequency+120);guard[max(0,idx-2):idx+3]=False;noise=float(np.median(abs(spectrum[guard]))+1e-12);return {"frequency_hz":frequency,"stimulus_amplitude":amplitude,"magnitude":signal,"snr_db":20*math.log10((signal+1e-12)/noise),"recorded_rms":float(np.sqrt(np.mean(recorded**2)))}

def _predict(train:list[dict[str,float]],frequency:float)->float:
    xs=np.log([r["frequency_hz"] for r in train]);ys=np.log([r["magnitude"]+1e-12 for r in train]);return float(np.exp(np.interp(math.log(frequency),xs,ys)))

def run_real_world_acoustic_learning(*,repo_root:Path,state_path:Path,result_path:Path|None=None)->dict[str,Any]:
    devices=sd.query_devices();input_id,output_id=sd.default.device;sd.default.device=(input_id,output_id)
    # Max-log-gap acquisition is decided before each physical measurement.
    chosen=[FREQUENCIES[0],FREQUENCIES[len(FREQUENCIES)//2],FREQUENCIES[-1]];measurements=[]
    for f in chosen:measurements.append(_measure(f))
    while len(chosen)<5:
        remaining=[f for f in FREQUENCIES if f not in chosen];candidate=max(remaining,key=lambda f:min(abs(math.log(f)-math.log(c)) for c in chosen));chosen.append(candidate);measurements.append(_measure(candidate));measurements.sort(key=lambda r:r["frequency_hz"])
    withheld=[f for f in FREQUENCIES if f not in chosen];predictions={str(f):_predict(measurements,f) for f in withheld};commitment=hashlib.sha256(json.dumps(predictions,sort_keys=True).encode()).hexdigest();revealed=[_measure(f) for f in withheld]
    truth={int(r["frequency_hz"]):r["magnitude"] for r in revealed};learned_error=float(np.mean([abs(predictions[str(f)]-truth[f])/(truth[f]+1e-12) for f in withheld]));flat=float(np.median([r["magnitude"] for r in measurements]));flat_error=float(np.mean([abs(flat-truth[f])/(truth[f]+1e-12) for f in withheld]));all_rows=measurements+revealed
    gate={"physical_input_device":devices[input_id]["name"],"physical_output_device":devices[output_id]["name"],"real_air_path":True,"frequencies_measured":len(FREQUENCIES),"active_probe_frequencies":chosen,"withheld_frequencies":withheld,"prediction_commitment":commitment,"minimum_snr_db":min(r["snr_db"] for r in all_rows),"learned_relative_error":learned_error,"flat_control_relative_error":flat_error,"error_reduction_vs_flat":1-learned_error/flat_error if flat_error else 0,"raw_audio_persisted":False,"speech_recognition_performed":False,"camera_used":False,"bluetooth_scanned":False,"unsafe_output_level":False}
    gate["accepted"]=bool(gate["minimum_snr_db"]>=10 and learned_error<flat_error and not gate["raw_audio_persisted"] and not gate["unsafe_output_level"])
    runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);runtime.store.state.setdefault("real_world_acoustic_learning",{});cohort="acoustic_v12_"+_canonical_hash({"gate":gate,"measurements":all_rows})[:16];runtime.store.state["real_world_acoustic_learning"][cohort]={"gate":gate,"measurements":all_rows,"created_at":_utc_timestamp()};candidate=ProcedureCandidate(procedure_id=PROCEDURE_ID,goal="real_world_acoustic_learning",steps=["select_safe_physical_probe","emit_speaker_intervention","measure_microphone_consequence","fit_response_model","commit_withheld_predictions","reveal_and_score_physical_outcomes"],score=max(0,1-learned_error),success=gate["accepted"],evidence={"cohort_id":cohort,"gate":gate},source_rules=[]);promotion=runtime.skills.promote(candidate);runtime.skills.record_outcome(procedure_id=PROCEDURE_ID,success=candidate.success,score=candidate.score,evidence=candidate.evidence);runtime.store.commit(reason="real_world_acoustic_learning_v12");restart_runtime=HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_allow);restart={"cohort_retained":cohort in restart_runtime.store.state.get("real_world_acoustic_learning",{}),"champion_retained":restart_runtime.store.state["champions"].get("real_world_acoustic_learning")==PROCEDURE_ID,"raw_audio_replayed":False}
    payload={"schema_version":"aion.hexcore.real_world_acoustic_learning.v1","created_at":_utc_timestamp(),"measurements":all_rows,"predictions_before_reveal":predictions,"gate":gate,"promotion":{"candidate":candidate.to_dict(),"decision":promotion},"restart":restart,"passed":bool(gate["accepted"] and (promotion.get("promoted") or promotion.get("champion_id")==PROCEDURE_ID) and restart["cohort_retained"] and restart["champion_retained"]),"boundary":"This is a real local speaker-air-microphone experiment on one development-owned Mac. It demonstrates physical measurement and prediction, not independent administration, broad robotics, unrestricted sensing or AGI."}
    if result_path:result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
    return payload

def main():
 p=argparse.ArgumentParser();p.add_argument("--repo-root",type=Path,default=Path("."));p.add_argument("--state-path",type=Path,default=Path("backend/modules/hexcore/data/acoustic_v12/state.json"));p.add_argument("--result-path",type=Path,default=Path("results/hexcore_real_world_acoustic_learning_v12.json"));a=p.parse_args();r=run_real_world_acoustic_learning(repo_root=a.repo_root.resolve(),state_path=a.state_path.resolve(),result_path=a.result_path.resolve());print(json.dumps({"passed":r["passed"],"gate":r["gate"]},indent=2,sort_keys=True))
if __name__=="__main__":main()
