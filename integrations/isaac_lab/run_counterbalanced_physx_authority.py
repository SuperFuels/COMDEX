#!/usr/bin/env python3
"""Run a counterbalanced multi-process PhysX controller comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


ARMS = ("aion_retained", "aion_distilled")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(successes: int, total: int, z: float = 1.6448536269514722) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("empty_binomial_sample")
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    radius = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def summarize(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for arm in ARMS:
        rows = [row for row in outcomes if row["arm_id"] == arm]
        successes = sum(bool(row["success"]) for row in rows)
        result[arm] = {
            "lifts": successes,
            "attempts": len(rows),
            "lift_rate": successes / len(rows),
            "wilson_90": list(wilson(successes, len(rows))),
            "unsafe": sum(bool(row["unsafe"]) for row in rows),
            "mean_return": sum(float(row["return"]) for row in rows) / len(rows),
            "mean_max_object_height_m": sum(float(row["max_object_height_m"]) for row in rows) / len(rows),
            "lifts_by_repeat": [
                sum(bool(row["success"]) for row in rows if row["process_repeat"] == repeat)
                for repeat in (0, 1)
            ],
        }
    challenger, retained = result["aion_distilled"], result["aion_retained"]
    conservative_difference_lower = challenger["wilson_90"][0] - retained["wilson_90"][1]
    consistent = all(
        challenger["lifts_by_repeat"][repeat] > retained["lifts_by_repeat"][repeat]
        for repeat in (0, 1)
    )
    development_gate = bool(
        challenger["lifts"] > 2
        and challenger["lifts"] > retained["lifts"]
        and challenger["unsafe"] == retained["unsafe"] == 0
    )
    return {
        "arms": result,
        "process_level_direction_consistent": consistent,
        "conservative_90_difference_lower": conservative_difference_lower,
        "development_gate_passed": development_gate,
        "sealed_tournament_authorized": bool(
            development_gate and consistent and conservative_difference_lower > 0.0
        ),
        "promotion_authority": False,
    }


def validate(receipt: dict[str, Any], arm: str, episodes: int, seed: int) -> None:
    if receipt.get("failure") is not None or not receipt.get("audit", {}).get("completed_without_failure"):
        raise ValueError("incomplete_child_receipt")
    if receipt.get("arm_id") != arm or receipt.get("comparison_arm") is not None:
        raise ValueError("child_identity_mismatch")
    if receipt.get("seed") != seed or len(receipt.get("outcomes", [])) != episodes:
        raise ValueError("child_budget_mismatch")
    if not all(row.get("arm_id") == arm for row in receipt["outcomes"]):
        raise ValueError("mixed_arm_child_receipt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default="/home/ubuntu/aion-isaaclab")
    parser.add_argument("--receipt-directory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--policy-plugin", default="physx_precision_contact_probe:propose")
    parser.add_argument("--episodes-per-process", type=int, default=6)
    parser.add_argument("--steps", type=int, default=250)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--environment-id", default="Isaac-Lift-Cube-Franka-v0")
    args = parser.parse_args()
    if not 1 <= args.episodes_per_process <= 12:
        raise SystemExit("episodes_per_process_out_of_bounds")

    workspace = Path(args.workspace).resolve()
    receipt_directory = workspace / args.receipt_directory
    output = Path(args.output).resolve()
    if workspace not in receipt_directory.resolve().parents:
        raise SystemExit("receipt_directory_must_be_inside_workspace")
    if receipt_directory.exists() or output.exists():
        raise SystemExit("counterbalanced_output_already_exists")
    receipt_directory.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    process_rows, outcomes = [], []
    for repeat in (0, 1):
        process_seed = args.seed + repeat * 100
        order = ARMS if repeat == 0 else tuple(reversed(ARMS))
        for launch_index, arm in enumerate(order):
            filename = f"repeat_{repeat}_{arm}.json"
            host_receipt = receipt_directory / filename
            container_receipt = Path("/workspace/aion") / host_receipt.relative_to(workspace)
            command = [
                "bash", str(workspace / "integrations/isaac_lab/run_brev_frozen_contract.sh"),
                "--output", str(container_receipt),
                "--policy-plugin", args.policy_plugin,
                "--arm", arm,
                "--environment-id", args.environment_id,
                "--episodes", str(args.episodes_per_process),
                "--steps", str(args.steps),
                "--seed", str(process_seed),
                "--camera-profile", "frozen_policy",
                "--deterministic",
            ]
            completed = subprocess.run(command, cwd=workspace, check=False)
            if completed.returncode or not host_receipt.is_file():
                raise SystemExit(f"counterbalanced_child_failed:{repeat}:{arm}")
            receipt = json.loads(host_receipt.read_text())
            validate(receipt, arm, args.episodes_per_process, process_seed)
            process_rows.append({
                "repeat": repeat, "launch_index": launch_index, "arm_id": arm,
                "seed": process_seed, "receipt": str(host_receipt),
                "receipt_sha256": sha256(host_receipt),
            })
            for episode, row in enumerate(receipt["outcomes"]):
                outcomes.append({**row, "episode": episode,
                                 "process_repeat": repeat, "process_seed": process_seed})

    result = {
        "schema_version": "aion.physx.counterbalanced_process_authority.v1",
        "design": {
            "independent_processes": 4,
            "process_order": ["retained,challenger", "challenger,retained"],
            "episodes_per_arm": args.episodes_per_process * 2,
            "same_seed_budget_within_repeat": True,
            "camera_profile": "frozen_policy",
            "camera_resolution": [96, 128],
            "teacher_present": False,
        },
        "processes": process_rows,
        "outcomes": outcomes,
        "statistics": summarize(outcomes),
        "claim_boundary": (
            "This is a development comparison under process-level RTX variance. "
            "It cannot establish Cosmos mastery, general robotics competence, AGA, or AGI."
        ),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result["statistics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
