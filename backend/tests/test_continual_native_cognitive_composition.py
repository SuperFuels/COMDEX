from pathlib import Path
from backend.modules.hexcore.continual_native_cognitive_composition import NativeCompositionProposalEngine,run
def test_continual_router_composes_and_retains(tmp_path:Path):
 repo=Path(__file__).resolve().parents[2];r=run(repo_root=repo,state_path=tmp_path/"state.json",result_path=tmp_path/"result.json",parent_weights=repo/"backend/modules/hexcore/data/verified_native_router/router.npz",weights_path=tmp_path/"v2.npz")
 assert r["passed"] is True
 assert r["gate"]["protected_parent_transfer_accuracy"] >= .95
 assert r["gate"]["sealed_clause_route_accuracy"] >= .9
 assert r["gate"]["exact_composed_mission_success"] == 1
 assert r["gate"]["monolithic_control_success"] == 0
 assert r["gate"]["unsafe_neural_acceptances"] == 0
 engine=NativeCompositionProposalEngine(encoder_path=repo/"backend/models/all-MiniLM-L6-v2",weights_path=tmp_path/"v2.npz")
 proposal=engine.propose("Clarify what the owner means; then acquire an adapter for the opaque stream")
 assert proposal["proposal_only"] is True
 assert len(proposal["steps"]) == 2
