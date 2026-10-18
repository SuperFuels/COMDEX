#!/usr/bin/env python3
"""Build a bounded lossless expert-local pack from existing verified frames."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


COMPONENTS = tuple((projection, kind) for projection in ("gate", "up", "down")
                   for kind in ("weight", "bias"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse-manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--experts", type=int, default=32)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.pack.exists() or args.manifest.exists():
        raise SystemExit("refusing to overwrite route-local evidence")
    warehouse = json.loads(args.warehouse_manifest.read_text())
    trace = json.loads(args.trace.read_text())
    counts = collections.Counter(
        expert for token in trace["run_a"]["tokens"]
        for expert in token["layers"][args.layer]["route"])
    selected = [expert for expert, _ in counts.most_common(args.experts)]
    addresses = {}
    for region in warehouse["regions"]:
        prefix = f"blk.{args.layer}.ffn_"
        if not region["region_name"].startswith(prefix):
            continue
        suffix = region["region_name"][len(prefix):]
        if "_exps." not in suffix:
            continue
        projection, kind = suffix.split("_exps.")
        if (projection, kind) not in COMPONENTS:
            continue
        for frame in region["frames"]:
            addresses[(int(frame["expert"]), projection, kind)] = {
                **frame, "path": str((args.warehouse_manifest.parent
                                      / region["pack_relative_path"]).resolve())}
    args.pack.parent.mkdir(parents=True, exist_ok=True)
    entries = {}
    pack_hash = hashlib.sha256()
    offset = 0
    with args.pack.open("xb", buffering=0) as output:
        for expert in selected:
            start = offset
            components = []
            for projection, kind in COMPONENTS:
                address = addresses[(expert, projection, kind)]
                fd = os.open(address["path"], os.O_RDONLY)
                try:
                    encoded = os.pread(fd, int(address["compressed_bytes"]),
                                       int(address["encoded_offset"]))
                finally:
                    os.close(fd)
                encoded_hash = hashlib.sha256(encoded).hexdigest()
                if len(encoded) != int(address["compressed_bytes"]) or encoded_hash != address["compressed_sha256"]:
                    raise RuntimeError("source compressed frame failed verification")
                output.write(encoded)
                pack_hash.update(encoded)
                components.append({
                    "projection": projection, "kind": kind,
                    "relative_offset": offset - start,
                    "compressed_bytes": len(encoded),
                    "compressed_sha256": encoded_hash,
                    "raw_bytes": int(address["raw_bytes"]),
                    "raw_sha256": address["raw_sha256"],
                })
                offset += len(encoded)
            entries[str(expert)] = {
                "offset": start, "compressed_bytes": offset - start,
                "components": components,
            }
    report = {
        "schema": "aion.gptoss-120b-route-local-micropack.v1",
        "status": "COMPLETE_VERIFIED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "source_manifest": str(args.warehouse_manifest.resolve()),
        "source_manifest_sha256": hashlib.sha256(args.warehouse_manifest.read_bytes()).hexdigest(),
        "trace": str(args.trace.resolve()),
        "trace_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "layer": args.layer,
        "selection": "most-frequent experts in frozen run_a trace",
        "experts": selected,
        "pack": str(args.pack.resolve()),
        "pack_bytes": offset,
        "pack_sha256": pack_hash.hexdigest(),
        "entries": entries,
        "claim_boundary": (
            "This bounded pack duplicates already-verified compressed frames for one layer "
            "and places each expert's six components contiguously. It changes storage layout "
            "only, not compressed bytes or neural values, and is not a full-model pack."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "pack_bytes": offset,
                      "experts": len(selected),
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
