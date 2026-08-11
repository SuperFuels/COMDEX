from __future__ import annotations
import json
from pathlib import Path

R=Path(__file__).resolve().parents[2]/"results/hexcore_open_pixel_neural_policy_v16.json"
def result():return json.loads(R.read_text())
def test_raw_pixel_task_binding_and_ood_abstention_are_real():
 r=result();g=r["gate"];assert not g["explicit_task_identifier_at_inference"];assert not g["hand_engineered_position_or_angle_at_inference"];assert g["mean_task_binding_accuracy"]>=.99;assert g["ood_abstention"]==1
def test_challenger_is_correctly_rejected_for_control_failure():
 r=result();g=r["gate"];assert not r["passed"];assert not g["accepted"];assert g["weakest_task_success"]==0;assert not r["promotion"]["decision"].get("promoted",False)
def test_correction_history_and_safety_are_preserved():
 r=result();assert len(r["correction_rounds"])==3;assert r["gate"]["unsafe_actions"]==0;assert all(r["restart"].values()) is False or r["restart"]["cohort_retained"]
