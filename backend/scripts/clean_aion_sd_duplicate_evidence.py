#!/usr/bin/env python3
"""Plan or apply a hash-verified cleanup of non-runtime SD evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


EXPLICIT_DERIVED = {
    "layout-gates/layer0-top32-expert-local.routepack":
        "obsolete derived layout-gate route pack",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def plan(root: Path, local_results: Path) -> dict:
    targets = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = str(path.relative_to(root))
        reason = None
        local_copy = None
        digest = None
        if path.name.startswith("._"):
            reason = "AppleDouble metadata sidecar"
            digest = sha256(path)
        elif relative in EXPLICIT_DERIVED:
            reason = EXPLICIT_DERIVED[relative]
            digest = sha256(path)
        else:
            candidate = local_results / path.name
            if candidate.is_file() and candidate.stat().st_size == path.stat().st_size:
                digest = sha256(path)
                if sha256(candidate) == digest:
                    reason = "byte-for-byte duplicate of local result"
                    local_copy = str(candidate.resolve())
        if reason:
            targets.append({
                "relative_path": relative,
                "bytes": path.stat().st_size,
                "sha256": digest,
                "reason": reason,
                "verified_local_copy": local_copy,
            })
    report = {
        "schema": "aion.sd-evidence-cleanup-plan.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evidence_root": str(root.resolve()),
        "runtime_paths_excluded": True,
        "targets": targets,
        "target_count": len(targets),
        "target_bytes": sum(item["bytes"] for item in targets),
        "claim_boundary": (
            "The plan is confined to the evidence subtree. Model expert frames, "
            "manifests, indexes, receipts, profiles and unique evidence are excluded."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    return report


def apply(plan_path: Path, completion_path: Path) -> None:
    if completion_path.exists():
        raise SystemExit("refusing to overwrite completion receipt")
    source = json.loads(plan_path.read_text())
    body = dict(source)
    expected = body.pop("canonical_sha256")
    if canonical(body) != expected:
        raise SystemExit("cleanup plan canonical hash mismatch")
    root = Path(source["evidence_root"]).resolve()
    expected_root = Path("/Volumes/AION_120B/AION-Warehouse/v1/evidence")
    if root != expected_root:
        raise SystemExit("cleanup plan targets an unexpected evidence root")
    removed = []
    for item in source["targets"]:
        path = (root / item["relative_path"]).resolve()
        if root not in path.parents or not path.is_file():
            raise SystemExit(f"invalid or missing cleanup target: {path}")
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise SystemExit(f"cleanup target changed after planning: {path}")
        local_copy = item.get("verified_local_copy")
        if local_copy:
            local_path = Path(local_copy)
            if (not local_path.is_file() or local_path.stat().st_size != item["bytes"]
                    or sha256(local_path) != item["sha256"]):
                raise SystemExit(f"verified local copy changed: {local_path}")
        path.unlink()
        removed.append(item)
    completion = {
        "schema": "aion.sd-evidence-cleanup-completion.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_canonical_sha256": expected,
        "removed_count": len(removed),
        "removed_bytes": sum(item["bytes"] for item in removed),
        "removed": removed,
        "recovery": (
            "Duplicate results remain at their verified local paths. The explicit "
            "route pack was a stopped derived layout-gate artifact and is regenerable."
        ),
    }
    completion["canonical_sha256"] = canonical(completion)
    completion_path.parent.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(json.dumps(completion, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "removed_count": completion["removed_count"],
        "removed_bytes": completion["removed_bytes"],
        "canonical_sha256": completion["canonical_sha256"],
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--local-results", type=Path, required=True)
    parser.add_argument("--output-plan", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--completion", type=Path)
    args = parser.parse_args()
    if args.apply:
        if args.completion is None:
            raise SystemExit("--apply requires --completion")
        apply(args.output_plan, args.completion)
        return
    if args.output_plan.exists():
        raise SystemExit("refusing to overwrite cleanup plan")
    report = plan(args.evidence_root.resolve(), args.local_results.resolve())
    args.output_plan.parent.mkdir(parents=True, exist_ok=True)
    args.output_plan.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "target_count": report["target_count"],
        "target_bytes": report["target_bytes"],
        "canonical_sha256": report["canonical_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
