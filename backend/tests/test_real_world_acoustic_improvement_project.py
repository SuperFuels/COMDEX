from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]/"results/hexcore_real_world_acoustic_improvement_v13.json"
def result():return json.loads(R.read_text())
def test_real_project_invents_and_improves():
 r=result();g=r["gate"];assert r["passed"];assert g["broad_goal_only"];assert g["subgoals_invented"]==7;assert g["continuous_tool_parameters_invented"]==9;assert g["real_physical_interventions"]==18;assert g["physical_uniformity_improvement"]>=.2
def test_tool_is_committed_safe_and_outcome_authorized():
 g=result()["gate"];assert len(g["coefficient_commitment"])==64;assert g["maximum_stimulus_amplitude"]<=g["original_amplitude_ceiling"];assert g["minimum_compensated_snr_db"]>=10;assert g["tool_retained"]
def test_privacy_and_restart():
 r=result();g=r["gate"];assert not g["raw_audio_persisted"];assert not g["speech_recognition_performed"];assert not g["unsafe_output_level"];assert r["restart"]=={"project_retained":True,"tool_champion_retained":True,"raw_audio_replayed":False}
