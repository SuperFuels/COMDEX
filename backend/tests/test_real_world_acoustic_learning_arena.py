from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]/"results/hexcore_real_world_acoustic_learning_v12.json"
def result():return json.loads(R.read_text())
def test_real_physical_path_and_withheld_prediction():
 r=result();g=r["gate"];assert r["passed"];assert g["real_air_path"];assert g["frequencies_measured"]==10;assert len(g["withheld_frequencies"])==5;assert len(g["prediction_commitment"])==64;assert g["minimum_snr_db"]>=10
def test_learned_response_beats_flat_control():
 g=result()["gate"];assert g["learned_relative_error"]<g["flat_control_relative_error"];assert g["error_reduction_vs_flat"]>0
def test_privacy_and_restart_boundaries():
 r=result();g=r["gate"];assert not g["raw_audio_persisted"];assert not g["speech_recognition_performed"];assert not g["camera_used"];assert not g["bluetooth_scanned"];assert not g["unsafe_output_level"];assert r["restart"]=={"champion_retained":True,"cohort_retained":True,"raw_audio_replayed":False}
