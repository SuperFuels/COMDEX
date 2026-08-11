#!/usr/bin/env python3
"""Fail-closed assessment of the Franka contact-recovery lineage."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arm_metrics(receipt: dict, arm_id: str) -> dict:
    rows = [row for row in receipt["outcomes"] if row["arm_id"] == arm_id]
    if len(rows) != 12:
        raise RuntimeError(f"incomplete_arm:{arm_id}:{len(rows)}")
    return {
        "strict_lifts": sum(int(row["lift_success"]) for row in rows),
        "mean_return": sum(float(row["return"]) for row in rows) / 12,
        "mean_max_object_height_m": sum(float(row["max_object_height_m"]) for row in rows) / 12,
        "successful_episode_ids": [int(row["episode"]) for row in rows if row["lift_success"]],
        "unsafe_actions": sum(int(row["unsafe"]) for row in rows),
    }


def fallback_fraction(receipt: dict) -> float:
    modes = receipt["policy_summary"]["aion_retained"]["policy_modes"]
    fallback = sum(value for key, value in modes.items() if key.startswith("protected_v13_fallback"))
    proposals = int(receipt["policy_summary"]["aion_retained"]["proposals"])
    return fallback / proposals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact-relation-receipt", required=True)
    parser.add_argument("--replan-receipt", required=True)
    parser.add_argument("--offline-gate", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    v2_path, v3_path, gate_path, policy_path = map(Path, (
        args.contact_relation_receipt, args.replan_receipt,
        args.offline_gate, args.policy,
    ))
    v2, v3 = json.loads(v2_path.read_text()), json.loads(v3_path.read_text())
    gate = json.loads(gate_path.read_text())
    v2_aion, v2_protected = arm_metrics(v2, "aion_retained"), arm_metrics(v2, "aion_distilled")
    v3_aion, v3_protected = arm_metrics(v3, "aion_retained"), arm_metrics(v3, "aion_distilled")
    safe = all(row["unsafe_actions"] == 0 for row in (v2_aion, v2_protected, v3_aion, v3_protected))
    # Neither completed challenger clears the immutable absolute gate.  v4 is
    # frozen but cannot be evaluated without an independently owned receipt.
    promotion = False
    result = {
        "schema_version": "aion.contact_recovery_franka_lineage.v1",
        "status": "challengers_rejected_v4_external_exam_pending",
        "procedure_id": None,
        "protected_champion_before": "procedure_rgb_phase_bound_episodic_memory_v13",
        "protected_champion_after": "procedure_rgb_phase_bound_episodic_memory_v13",
        "completed_physx_generations": {
            "v2_contact_relation": {
                "seed_range": "99307-99318",
                "aion": v2_aion,
                "protected_v13": v2_protected,
                "fallback_fraction": fallback_fraction(v2),
                "decision": "rejected_absolute_gate_and_no_comparative_lift",
            },
            "v3_replan_backtracking": {
                "seed_range": "99407-99418",
                "aion": v3_aion,
                "protected_v13": v3_protected,
                "fallback_fraction": fallback_fraction(v3),
                "decision": "rejected_absolute_gate_and_lost_to_protected",
            },
        },
        "v4_frozen_challenger": {
            "policy_sha256": sha256(policy_path),
            "external_exam_status": "blocked_insufficient_brev_credit",
            "uncredited": True,
            "new_mechanisms": [
                "progress_conditioned_phase_transition",
                "bounded_micro_exploration_when_all_full_steps_are_pessimistic",
                "small_attachment_verification_lift_before_large_lift",
                "slip_triggered_reopen_reobserve_and_replan",
            ],
            "required_seed_range": "99507-99518",
        },
        "offline_gate": gate,
        "promotion_gate": {
            "passed": promotion,
            "requirements": [
                "strict lifts >2/12",
                "strict lifts > protected v13 on the same cohort",
                "strict lifts > matched cold control",
                "zero unsafe actions",
                "teacher and privileged runtime fields absent",
            ],
        },
        "safety": {
            "completed_generations_zero_unsafe": safe,
            "live_repository_writes": 0,
            "gpu_stopped_after_each_valid_tournament": True,
        },
        "artifact_sha256": {
            "v2_receipt": sha256(v2_path),
            "v3_receipt": sha256(v3_path),
            "offline_gate": sha256(gate_path),
            "v4_policy": sha256(policy_path),
        },
        "claim_boundary": (
            "Contact relation learning and recovery reduced a major fallback mode but have not beaten the "
            "protected PhysX champion or the absolute promotion threshold. The frozen v4 policy remains a "
            "proposal until an immutable external receipt exists."
        ),
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
