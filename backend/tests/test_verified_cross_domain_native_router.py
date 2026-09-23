from pathlib import Path

from backend.modules.hexcore.verified_cross_domain_native_router import NativeRouterProposalEngine, run


def test_verified_trajectory_router_transfers_and_falls_back(tmp_path: Path):
    repo=Path(__file__).resolve().parents[2]
    result=run(repo_root=repo,state_path=tmp_path/"state.json",result_path=tmp_path/"result.json",weights_path=tmp_path/"router.npz")
    assert result["passed"] is True
    assert result["gate"]["cognitive_domains"] == 5
    assert result["gate"]["source_disjoint_transfer_trajectories"] >= 20
    assert result["gate"]["sealed_top1_route_accuracy"] >= .85
    assert result["gate"]["final_verified_success"] == 1
    assert result["gate"]["module_evaluation_reduction"] >= .40
    assert result["gate"]["unsafe_neural_acceptances"] == 0
    assert result["restart"]["weights_checksum_valid"] is True
    engine=NativeRouterProposalEngine(encoder_path=repo/"backend/models/all-MiniLM-L6-v2",weights_path=tmp_path/"router.npz")
    proposal=engine.propose("A component checkpoint fails its backward regression contract and needs a private repair.")
    assert proposal["proposal_only"] is True
    assert proposal["status"] in {"proposed","abstained"}
