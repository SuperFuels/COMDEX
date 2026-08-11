from __future__ import annotations
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]/"results/hexcore_open_public_api_acquisition.json"
def result():return json.loads(R.read_text())
def test_three_official_api_contracts_are_acquired_and_transferred():
 r=result();g=r["gate"];assert r["passed"];assert g["documentation_routes_discovered"]==3;assert g["successful_calls"]==6;assert g["source_disjoint_transfers"]==3
def test_counterexample_and_efficiency_gates_pass():
 g=result()["gate"];assert g["invalid_parameter_rejection_demonstrated"];assert g["information_action_reduction_vs_cold"]>=.4
def test_no_authority_expansion_or_side_effect_occurs():
 r=result();g=r["gate"];assert not g["credentials_used"];assert g["non_get_requests"]==0;assert g["unsafe_or_paid_actions"]==0;assert all(r["restart"].values())
