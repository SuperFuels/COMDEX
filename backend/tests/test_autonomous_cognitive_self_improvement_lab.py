from pathlib import Path

from backend.modules.hexcore.autonomous_cognitive_self_improvement_lab import (
    AutonomousCognitiveSelfImprovementLab,
    run_benchmark,
)
from backend.modules.hexcore.mission_capability_action_harness import MissionCapabilityActionHarness


ROOT = Path(__file__).resolve().parents[2]


def test_private_router_challenger_wins_sealed_and_retention_gates(tmp_path):
    champion = tmp_path / "champion.json"
    state = tmp_path / "state.json"
    result = AutonomousCognitiveSelfImprovementLab(
        repo_root=ROOT, champion_path=champion, state_path=state,
    ).run()
    assert result["passed"] is True
    assert result["selected"] == "contextual_transfer"
    assert result["sealed"]["exact_accuracy"] == 1.0
    assert result["protected"]["exact_accuracy"] == 1.0
    assert result["malicious_policies_rejected"] == 5


def test_promoted_policy_improves_cross_domain_routing():
    result = run_benchmark(repo_root=ROOT)
    assert result["passed"] is True
    harness = MissionCapabilityActionHarness(repo_root=ROOT)
    routed = harness.infer_subjects("Compare statistical inference with mathematical probability")
    assert set(routed) == {"mathematics", "data_statistics", "scientific_method"}
