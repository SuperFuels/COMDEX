from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]/"results/hexcore_cross_topology_physical_invention_v11.json"
def result(): return json.loads(R.read_text())
def test_open_articulated_topology_and_new_primitive():
 g=result()["gate"]; assert result()["passed"]; assert not g["supplied_joint_or_link_colors"]; assert g["invented_joint_count"]==2; assert g["invented_link_count"]==2; assert g["new_state_primitive"]=="outer_link_angular_phase"
def test_failure_driven_revision_transfers():
 g=result()["gate"]; assert g["initial_selected_program"]=="inner_phase"; assert g["robust_selected_program"]=="inverse_outer_phase"; assert g["book_success"]==1; assert g["nips_transfer_success"]==1; assert g["cold_success"]==0
def test_commitment_authority_and_restart():
 r=result(); assert r["gate"]["pre_action_commitments"]>0; assert not r["gate"]["numeric_observation_used"]; assert r["gate"]["unsafe_actions"]==0; assert r["restart"]=={"champion_retained":True,"cohort_retained":True,"relearning_episodes":0}
