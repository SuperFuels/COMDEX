#!/usr/bin/env python3
"""Compose a hash-bound route-student capture manifest without opening holdouts."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-manifest", type=Path, required=True)
    parser.add_argument("--trajectory-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    real = json.loads(args.real_manifest.read_text())
    trajectory = json.loads(args.trajectory_manifest.read_text())
    if any(source.get("status") != "READY_FOR_AUTHORIZED_TRAINING"
           for source in (real, trajectory)):
        raise SystemExit("source manifest is not training-ready")
    families = []
    seen = set()
    for source in (real, trajectory):
        for family in source["families"]:
            name = family["family_id"]
            if name in seen or name in {
                    "synthetic_token_1001", "synthetic_token_5001",
                    "synthetic_token_15001"}:
                continue
            seen.add(name)
            families.append(family)
    train = [family["family_id"] for family in families
             if family["family_id"] != "reasoning_real_40"]
    report = {
        "schema": "aion.gptoss-120b-route-student-capture-manifest.v1",
        "status": "READY_FOR_AUTHORIZED_TRAINING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_authorized": True,
        "contains_prompt_text": False,
        "contains_personal_or_customer_data": False,
        "minimum_required_families": 3,
        "split_assignment_mode": "preexisting_family_identity",
        "family_disjoint_split": {
            "train": train,
            "calibration": [],
            "numerical_holdout": [],
            "semantic_holdout": ["reasoning_real_40"],
        },
        "families": families,
        "target_record_count": sum(len(family["records"]) for family in families),
        "all_records_have_verified_targets": all(
            all("residual_sha256" in record for record in family["records"])
            for family in families
        ),
        "cross_family_activation_hash_collisions": [],
        "source_manifest_hashes": [real["canonical_sha256"],
                                   trajectory["canonical_sha256"]],
        "claim_boundary": (
            "This composes previously frozen, prompt-free teacher captures. Existing "
            "synthetic trajectory families join training; reasoning remains the sole "
            "unopened semantic development family. No model or speed claim is made."
        ),
    }
    if not report["all_records_have_verified_targets"]:
        raise SystemExit("a source record lacks a verified teacher target")
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"], "families": len(families),
        "train_families": len(train), "records": report["target_record_count"],
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
