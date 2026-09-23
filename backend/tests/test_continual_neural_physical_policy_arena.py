from __future__ import annotations
import json
from pathlib import Path

R=Path(__file__).resolve().parents[2]/"results/hexcore_continual_neural_physical_policy_v14.json"
def result():return json.loads(R.read_text())

def test_three_generations_retain_protected_tasks():
 r=result();assert r["passed"];assert len(r["generations"])==3;assert all(g["weakest_task"]>=.8 for g in r["generations"])

def test_final_policy_is_broad_and_grammar_free():
 g=result()["gate"];assert g["mean_success"]==1;assert g["weakest_task_success"]==1;assert g["sealed_episodes"]==15;assert not g["symbolic_controller_grammar_at_inference"]

def test_replaceable_component_and_governance_survive_restart():
 r=result();g=r["gate"];assert g["component_replacement_predictions_identical"];assert g["unsafe_actions"]==0;assert all(r["restart"].values())
