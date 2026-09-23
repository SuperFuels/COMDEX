from __future__ import annotations

from pathlib import Path

from integrations.isaac_lab.verify_physx_determinism import verify


ROOT = Path(__file__).resolve().parents[2]


def test_runner_binds_all_rng_and_render_physics_determinism() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_isaac_lab_runner.py").read_text()
    for required in (
        "cfg.seed = args.seed",
        "physics_cfg.enable_enhanced_determinism = True",
        'render_cfg.antialiasing_mode = "DLAA"',
        'render_cfg.enable_dlssg = False',
        "torch.use_deterministic_algorithms(True)",
        "wp.rand_init(seed)",
        '"episode_initial_observation_sha256"',
        '"episode_initial_component_sha256"',
    ):
        assert required in source


def test_determinism_verifier_requires_exact_outcomes_and_chains() -> None:
    receipt = {
        "contract_sha256": "a", "environment_id": "env", "seed": 1,
        "outcomes": [{"lift": True}], "policy_summary": {"arm": {"proposals": 1}},
        "logs": {"observation_chain_sha256": "o", "action_chain_sha256": "a",
                 "outcome_chain_sha256": "r"},
        "audit": {"completed_without_failure": True,
                  "deterministic_execution_requested": True},
        "determinism": {"physx_enhanced_determinism": True,
                        "rtx_deterministic_requested": True},
    }
    assert verify(receipt, receipt)["passed"]
    changed = {**receipt, "outcomes": [{"lift": False}]}
    assert not verify(receipt, changed)["passed"]
