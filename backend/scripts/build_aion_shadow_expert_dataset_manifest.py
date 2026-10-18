#!/usr/bin/env python3
"""Create a hash-bound, family-disjoint Shadow Expert dataset manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", action="append", required=True,
                        help="FAMILY_ID=CAPTURE_DIRECTORY")
    parser.add_argument("--split", action="append", default=[],
                        help="FAMILY_ID=train|calibration|numerical_holdout|semantic_holdout")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    families = []
    seen_hashes = {}
    leakage = []
    for value in args.family:
        family_id, separator, directory_text = value.partition("=")
        if not separator or not family_id:
            raise SystemExit("family must use FAMILY_ID=CAPTURE_DIRECTORY")
        directory = Path(directory_text).resolve()
        records = []
        for metadata_path in sorted(directory.glob("position-*-layer-*.json")):
            metadata = json.loads(metadata_path.read_text()); stem = metadata_path.with_suffix("")
            ffn_path = Path(str(stem) + "-ffn.bin"); router_path = Path(str(stem) + "-router.bin")
            if digest(ffn_path) != metadata["ffn_sha256"] or digest(router_path) != metadata["router_sha256"]:
                raise RuntimeError("activation capture failed hash verification")
            activation_key = metadata["router_sha256"]
            if activation_key in seen_hashes and seen_hashes[activation_key] != family_id:
                leakage.append({"activation_sha256": activation_key,
                                "families": sorted({seen_hashes[activation_key], family_id})})
            seen_hashes[activation_key] = family_id
            record = {"position": metadata["position"], "layer": metadata["layer"],
                            "route": metadata["route"], "gates": metadata["gates"],
                            "metadata_path": str(metadata_path),
                            "metadata_sha256": digest(metadata_path),
                            "ffn_path": str(ffn_path), "ffn_sha256": metadata["ffn_sha256"],
                            "router_path": str(router_path), "router_sha256": metadata["router_sha256"]}
            if metadata.get("schema") == "aion.gptoss-120b-shadow-target-capture.v2":
                if metadata.get("contains_prompt_text") is not False:
                    raise RuntimeError("shadow capture does not explicitly exclude prompt text")
                if metadata.get("contains_personal_or_customer_data") is not False:
                    raise RuntimeError("shadow capture does not explicitly exclude personal/customer data")
                for name in ("output", "residual"):
                    path = Path(str(stem) + f"-{name}.bin")
                    if digest(path) != metadata[f"{name}_sha256"]:
                        raise RuntimeError(f"{name} target failed hash verification")
                    record[f"{name}_path"] = str(path)
                    record[f"{name}_sha256"] = metadata[f"{name}_sha256"]
                record["target_definition"] = metadata["target_definition"]
            records.append(record)
        families.append({"family_id": family_id, "capture_directory": str(directory),
                         "records": records, "record_count": len(records)})
    family_ids = sorted(item["family_id"] for item in families)
    # The split is family-disjoint and stable. At least four families are required so
    # train, calibration, numerical holdout and semantic holdout cannot share a family.
    split_names = ("train", "calibration", "numerical_holdout", "semantic_holdout")
    split_overrides = {}
    for value in args.split:
        family_id, separator, split_name = value.partition("=")
        if not separator or split_name not in split_names:
            raise SystemExit("split must use FAMILY_ID=train|calibration|numerical_holdout|semantic_holdout")
        if family_id in split_overrides:
            raise SystemExit("duplicate split assignment")
        split_overrides[family_id] = split_name
    if split_overrides and set(split_overrides) != set(family_ids):
        raise SystemExit("explicit split must assign every family exactly once")
    split = {name: [] for name in split_names}
    for index, family_id in enumerate(family_ids):
        split_name = split_overrides.get(family_id, split_names[index % len(split_names)])
        split[split_name].append(family_id)
    target_records = sum("residual_sha256" in record for family in families
                         for record in family["records"])
    total_records = sum(family["record_count"] for family in families)
    if len(family_ids) < 4 or not all(split.values()):
        status = "INSUFFICIENT_FAMILY_COVERAGE"
    elif leakage:
        status = "CROSS_FAMILY_ACTIVATION_LEAKAGE"
    elif target_records != total_records or total_records == 0:
        status = "INSUFFICIENT_TARGET_COVERAGE"
    else:
        status = "READY_FOR_AUTHORIZED_TRAINING"
    report = {
        "schema": "aion.shadow-expert-dataset-manifest.v1",
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contains_prompt_text": False, "contains_personal_or_customer_data": False,
        "families": families, "family_disjoint_split": split,
        "split_assignment_mode": "explicit_frozen" if split_overrides else "stable_round_robin",
        "cross_family_activation_hash_collisions": leakage,
        "target_record_count": target_records,
        "all_records_have_verified_targets": target_records == total_records and total_records > 0,
        "minimum_required_families": 4,
        "training_authorized": False,
        "claim_boundary": (
            "This manifest verifies numerical capture files and freezes a family-disjoint split. "
            "Readiness additionally requires a verified combined-residual target for every row. "
            "This manifest authorizes no training or weight injection."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "families": len(family_ids),
                      "records": sum(x["record_count"] for x in families),
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
