from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]/"results/hexcore_predictive_visual_dynamics_v17.json"
def result():return json.loads(R.read_text())
def test_predictive_latent_is_real_but_not_promoted():
 r=result();g=r["gate"];assert g["rgb_only_at_inference"];assert g["predictive_transition_objective"];assert g["training"]["latent_state_rmse"]<.1;assert not g["accepted"];assert not r["passed"]
def test_failure_is_closed_and_restart_auditable():
 r=result();assert r["gate"]["unsafe_actions"]==0;assert r["restart"]["cohort_retained"];assert not r["restart"]["champion_retained"];assert not r["promotion"]["decision"].get("promoted",False)
