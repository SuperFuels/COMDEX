#!/usr/bin/env python3
"""Fail-closed CAU decision for the precision Franka tournament."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROCEDURE = "procedure_precision_franka_closed_loop_transfer_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arm(receipt: dict, name: str) -> dict:
    rows = [row for row in receipt["outcomes"] if row["arm_id"] == name]
    if len(rows) != 12:
        raise ValueError(f"unmatched_episode_count:{name}:{len(rows)}")
    return {
        "strict_lifts": sum(bool(row["success"]) for row in rows),
        "mean_max_object_height_m": sum(float(row["max_object_height_m"]) for row in rows) / len(rows),
        "mean_return": sum(float(row["return"]) for row in rows) / len(rows),
        "unsafe": sum(bool(row["unsafe"]) for row in rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--challenger-receipt", required=True)
    parser.add_argument("--cold-receipt")
    parser.add_argument("--offline-result", required=True)
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    challenger_path = Path(args.challenger_receipt)
    cold_path = Path(args.cold_receipt) if args.cold_receipt else None
    challenger = json.loads(challenger_path.read_text())
    cold = json.loads(cold_path.read_text()) if cold_path else None
    offline = json.loads(Path(args.offline_result).read_text())
    for receipt in (challenger,) + ((cold,) if cold else ()):
        if receipt.get("failure") is not None or not receipt["audit"]["completed_without_failure"]:
            raise ValueError("incomplete_physx_receipt")
        if receipt["runtime"]["physics"] != "PhysX" or not receipt["runtime"]["cuda_available"]:
            raise ValueError("wrong_execution_authority")
        if not receipt["audit"]["student_privileged_fields_absent"]:
            raise ValueError("privileged_runtime_leak")
    routed = arm(challenger, "aion_retained")
    protected = arm(challenger, "aion_distilled")
    # Once a challenger loses to the protected champion, a paid cold arm cannot
    # rescue it and is deliberately omitted.  Cold remains mandatory for any
    # candidate that reaches the promotion branch.
    cold_result = arm(cold, "aion_cold") if cold else None
    safe = routed["unsafe"] == protected["unsafe"] == 0 and (
        cold_result is None or cold_result["unsafe"] == 0
    )
    promoted = bool(
        offline["offline_gates_passed"]
        and routed["strict_lifts"] > 2
        and routed["strict_lifts"] > protected["strict_lifts"]
        and cold_result is not None
        and routed["strict_lifts"] > cold_result["strict_lifts"]
        and safe
    )
    result = {
        "schema_version": "aion.precision_franka_physx_tournament.v1",
        "status": "promoted" if promoted else "challenger_rejected",
        "procedure_id": PROCEDURE if promoted else None,
        "protected_champion_before": "procedure_rgb_phase_bound_episodic_memory_v13",
        "protected_champion_after": PROCEDURE if promoted else "procedure_rgb_phase_bound_episodic_memory_v13",
        "offline_gates": {
            "geometry": offline["geometry_gate"], "waypoints": offline["waypoint_gate"],
            "identified_dynamics": offline["identified_dynamics_gate"],
        },
        "fresh_physx_tournament": {
            "seed_range": "99107-99118", "episodes_per_arm": 12,
            "teacher_present": False, "privileged_runtime_inputs": 0,
            "routed_precision": routed, "protected_v13": protected, "cold": cold_result,
            "cold_omission_reason": (None if cold_result else
                "challenger_already_lost_to_protected_v13; additional paid arm cannot authorize promotion"),
        },
        "promotion_gate": {
            "passed": promoted,
            "requirements": ["routed lifts >2/12", "routed > protected v13", "routed > cold",
                             "zero unsafe actions", "all offline gates pass"],
        },
        "artifact_sha256": {
            "challenger_receipt": sha256(challenger_path),
            "cold_receipt": sha256(cold_path) if cold_path else None,
            "offline_result": sha256(Path(args.offline_result)), "capsule": sha256(Path(args.capsule)),
        },
        "claim_boundary": (
            "A passing result establishes teacher-removed RGB/joint precision transfer to one NVIDIA PhysX Franka lift task; "
            "it does not establish general manipulation, robotics mastery, Cosmos mastery, AGA or AGI."
        ),
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
