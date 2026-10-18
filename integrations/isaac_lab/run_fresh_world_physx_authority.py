#!/usr/bin/env python3
"""Execute every PhysX arm/episode in an independent container and world.

This host-side authority deliberately pays the container startup cost in order
to remove sequential simulator, renderer, and contact-history leakage.  The
single-episode child receipts remain the primary evidence; the aggregate is a
fail-closed index over those immutable receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable


PERMITTED_ARMS = {
    "aion_retained", "aion_cold", "aion_cosmos", "gr00t_teacher", "aion_distilled",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_plan(arms: Iterable[str], episodes: int, seed: int) -> list[dict[str, Any]]:
    """Counterbalance launch order even though every execution is isolated."""
    ordered = list(arms)
    if not ordered or any(arm not in PERMITTED_ARMS for arm in ordered):
        raise ValueError("invalid_or_empty_arm_set")
    if len(set(ordered)) != len(ordered):
        raise ValueError("duplicate_arm")
    if not 1 <= episodes <= 24:
        raise ValueError("episode_count_out_of_bounds")
    plan = []
    for episode in range(episodes):
        rotated = ordered[episode % len(ordered):] + ordered[:episode % len(ordered)]
        for launch_index, arm in enumerate(rotated):
            plan.append({
                "arm_id": arm,
                "episode": episode,
                "seed": seed + episode,
                "launch_index_within_episode": launch_index,
            })
    return plan


def validate_child(receipt: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("failure") is not None:
        raise ValueError("child_receipt_failure")
    audit = receipt.get("audit", {})
    deterministic = receipt.get("determinism", {})
    if not (
        audit.get("completed_without_failure")
        and audit.get("deterministic_execution_requested")
        and deterministic.get("physx_enhanced_determinism")
        and deterministic.get("rtx_deterministic_requested")
    ):
        raise ValueError("child_determinism_authority_missing")
    if receipt.get("comparison_arm") is not None or receipt.get("matched_same_process"):
        raise ValueError("sequential_comparison_forbidden")
    if receipt.get("arm_id") != expected["arm_id"] or receipt.get("seed") != expected["seed"]:
        raise ValueError("child_identity_mismatch")
    outcomes = receipt.get("outcomes", [])
    if len(outcomes) != 1 or outcomes[0].get("arm_id") != expected["arm_id"]:
        raise ValueError("single_episode_child_required")
    summary = receipt.get("policy_summary", {}).get(expected["arm_id"], {})
    hashes = summary.get("episode_initial_observation_sha256", [])
    if len(hashes) != 1 or len(str(hashes[0])) != 64:
        raise ValueError("initial_observation_hash_missing")
    components = summary.get("episode_initial_component_sha256", [])
    if len(components) != 1 or components[0].get("rgb") != hashes[0] or any(
        len(str(components[0].get(field))) != 64
        for field in ("rgb", "proprioception", "fingertip_touch")
    ):
        raise ValueError("initial_component_hashes_missing")
    return dict(components[0])


def aggregate(children: list[tuple[dict[str, Any], Path, dict[str, Any]]]) -> dict[str, Any]:
    rows = []
    outcomes = []
    for expected, path, receipt in children:
        initial_components = validate_child(receipt, expected)
        outcome = dict(receipt["outcomes"][0])
        # Child policies correctly see episode zero in their new process.  The
        # authority assigns the precommitted global episode only after acting.
        outcome["episode"] = expected["episode"]
        outcomes.append(outcome)
        rows.append({
            **expected,
            "receipt": str(path),
            "receipt_sha256": sha256(path),
            "initial_observation_sha256": initial_components["rgb"],
            "initial_component_sha256": initial_components,
            "observation_chain_sha256": receipt["logs"]["observation_chain_sha256"],
            "action_chain_sha256": receipt["logs"]["action_chain_sha256"],
            "outcome_chain_sha256": receipt["logs"]["outcome_chain_sha256"],
        })
    return {
        "schema_version": "aion.physx.fresh_world_authority.v1",
        "world_isolation": "independent_container_simulation_app_world_per_arm_episode",
        "fresh_world_verified": True,
        "children": rows,
        "outcomes": outcomes,
        "audit": {
            "all_children_valid": True,
            "single_episode_per_process": True,
            "sequential_world_reuse": False,
            "promotion_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default="/home/ubuntu/aion-isaaclab")
    parser.add_argument("--receipt-directory", required=True,
                        help="New path relative to the workspace; existing files fail closed")
    parser.add_argument("--output", required=True)
    parser.add_argument("--policy-plugin", required=True)
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--steps", type=int, default=250)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--environment-id", default="Isaac-Lift-Cube-Franka-v0")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    receipt_directory = workspace / args.receipt_directory
    output = Path(args.output).resolve()
    if workspace not in receipt_directory.resolve().parents:
        raise SystemExit("receipt_directory_must_be_inside_workspace")
    if receipt_directory.exists() or output.exists():
        raise SystemExit("fresh_world_output_already_exists")
    receipt_directory.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    children = []
    plan = execution_plan(args.arms, args.episodes, args.seed)
    for item in plan:
        filename = f"episode_{item['episode']:02d}_{item['arm_id']}.json"
        host_receipt = receipt_directory / filename
        container_receipt = Path("/workspace/aion") / host_receipt.relative_to(workspace)
        command = [
            "bash", str(workspace / "integrations/isaac_lab/run_brev_frozen_contract.sh"),
            "--output", str(container_receipt),
            "--policy-plugin", args.policy_plugin,
            "--arm", item["arm_id"],
            "--environment-id", args.environment_id,
            "--episodes", "1",
            "--steps", str(args.steps),
            "--seed", str(item["seed"]),
            "--deterministic",
        ]
        completed = subprocess.run(command, cwd=workspace, check=False)
        if completed.returncode or not host_receipt.is_file():
            raise SystemExit(f"fresh_world_child_failed:{item['arm_id']}:{item['episode']}")
        receipt = json.loads(host_receipt.read_text())
        validate_child(receipt, item)
        children.append((item, host_receipt, receipt))

    result = aggregate(children)
    output.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({
        "output": str(output),
        "child_receipts": len(children),
        "fresh_world_verified": result["fresh_world_verified"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
