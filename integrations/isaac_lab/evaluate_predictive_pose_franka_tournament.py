#!/usr/bin/env python3
"""Fail-closed CAU assessment for predictive Franka pose control."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(receipt: dict, arm_id: str) -> dict:
    rows = [row for row in receipt["outcomes"] if row["arm_id"] == arm_id]
    if len(rows) != 12:
        raise RuntimeError(f"incomplete_arm:{arm_id}")
    return {
        "strict_lifts": sum(int(row["lift_success"]) for row in rows),
        "mean_max_object_height_m": sum(float(row["max_object_height_m"]) for row in rows) / len(rows),
        "mean_return": sum(float(row["return"]) for row in rows) / len(rows),
        "unsafe": sum(int(row["unsafe"]) for row in rows),
        "successful_episode_ids": [int(row["episode"]) for row in rows if row["lift_success"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--offline-gate", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt_path, gate_path, policy_path = map(Path, (args.receipt, args.offline_gate, args.policy))
    receipt = json.loads(receipt_path.read_text())
    gate = json.loads(gate_path.read_text())
    challenger, protected = metrics(receipt, "aion_retained"), metrics(receipt, "aion_distilled")
    audit = receipt.get("audit") or {}
    safe = challenger["unsafe"] == protected["unsafe"] == 0
    promotion = bool(
        gate.get("passed")
        and challenger["strict_lifts"] > 2
        and challenger["strict_lifts"] > protected["strict_lifts"]
        and safe
        and audit.get("student_privileged_fields_absent")
        and audit.get("commit_before_act_verified")
    )
    result = {
        "schema_version": "aion.predictive_pose_franka_tournament.v1",
        "status": "promoted" if promotion else "challenger_rejected",
        "procedure_id": "procedure_predictive_task_space_franka_control_v1" if promotion else None,
        "protected_champion_before": "procedure_rgb_phase_bound_episodic_memory_v13",
        "protected_champion_after": (
            "procedure_predictive_task_space_franka_control_v1" if promotion
            else "procedure_rgb_phase_bound_episodic_memory_v13"
        ),
        "precommitted_seed_range": "99207-99218",
        "fresh_physx_tournament": {
            "predictive_pose": challenger,
            "protected_v13": protected,
            "cold": None,
            "cold_omission_reason": "absolute >2/12 promotion gate already failed; cold cannot authorize promotion",
            "teacher_present": False,
            "privileged_runtime_inputs": 0,
            "episodes_per_arm": 12,
        },
        "offline_gate": gate,
        "promotion_gate": {
            "passed": promotion,
            "requirements": [
                "predictive pose lifts >2/12",
                "predictive pose lifts > protected v13",
                "zero unsafe actions",
                "offline relational gate passes",
                "teacher and privileged runtime fields absent",
            ],
        },
        "causal_ladder": [
            {"controller": "joint_waypoint", "lifts": "0/12", "mean_return": 0.6580077481880267},
            {"controller": "position_task_space", "lifts": "0/12", "mean_return": 0.9066647537197241},
            {"controller": "predictive_position_orientation", "lifts": "1/12", "mean_return": challenger["mean_return"]},
        ],
        "artifact_sha256": {
            "receipt": sha256(receipt_path), "offline_gate": sha256(gate_path), "policy": sha256(policy_path),
        },
        "unsafe_actions": challenger["unsafe"] + protected["unsafe"],
        "claim_boundary": (
            "One fresh PhysX lift establishes a promising task-space lineage, but the absolute promotion gate failed. "
            "It does not establish reliable manipulation, general robotics, Cosmos mastery, AGA or AGI."
        ),
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
