#!/usr/bin/env python3
"""Create a source-bound, expert-aligned packing plan from GGUF headers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index


EXPERT = re.compile(r"^blk\.(?P<layer>\d+)\.ffn_(?P<projection>down|gate|up)_exps\.(?P<kind>weight|bias)$")


def _canonical_hash(payload: dict) -> str:
    value = {key: item for key, item in payload.items() if key != "canonical_sha256"}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _frames(length: int, maximum: int) -> list[dict[str, int]]:
    result = []
    for index, start in enumerate(range(0, length, maximum)):
        result.append({"frame": index, "relative_offset": start,
                       "raw_bytes": min(maximum, length - start)})
    return result


def build_plan(source: dict, header_paths: list[Path], maximum_frame_bytes: int) -> dict:
    if maximum_frame_bytes <= 0:
        raise ValueError("maximum frame size must be positive")
    if len(header_paths) != len(source["shards"]):
        raise ValueError("one header sample is required for every shard")
    planned_shards = []
    expert_frames = 0
    other_frames = 0
    for shard_number, (shard, header_path) in enumerate(zip(source["shards"], header_paths), 1):
        with header_path.open("rb") as handle:
            index = read_gguf_stream_index(
                handle, int(shard["size"]),
                {"general.architecture", "general.name", "general.alignment"},
            )
        regions = [{
            "name": "__gguf_header__", "source_offset": 0,
            "raw_bytes": int(index["data_offset"]), "kind": "header",
            "frames": _frames(int(index["data_offset"]), maximum_frame_bytes),
        }]
        other_frames += len(regions[0]["frames"])
        for tensor in sorted(index["tensors"], key=lambda item: int(item["absolute_offset"])):
            match = EXPERT.match(tensor["name"])
            length = int(tensor["byte_length"])
            if match:
                expert_count = int(tensor["dimensions"][-1])
                if expert_count <= 0 or length % expert_count:
                    raise ValueError(f"expert tensor is not evenly sliceable: {tensor['name']}")
                stride = length // expert_count
                frames = [
                    {"frame": expert, "expert": expert,
                     "relative_offset": expert * stride, "raw_bytes": stride}
                    for expert in range(expert_count)
                ]
                kind = "expert_tensor"
                expert_frames += len(frames)
            else:
                frames = _frames(length, maximum_frame_bytes)
                kind = "shared_tensor"
                other_frames += len(frames)
            regions.append({
                "name": tensor["name"], "source_offset": int(tensor["absolute_offset"]),
                "raw_bytes": length, "kind": kind, "ggml_type": int(tensor["ggml_type"]),
                "dimensions": tensor["dimensions"], "frames": frames,
            })
        cursor = 0
        for region in regions:
            if region["source_offset"] != cursor:
                raise ValueError(f"source coverage gap in shard {shard_number} at {cursor}")
            if sum(frame["raw_bytes"] for frame in region["frames"]) != region["raw_bytes"]:
                raise ValueError(f"frame coverage mismatch for {region['name']}")
            cursor += region["raw_bytes"]
        if cursor != int(shard["size"]):
            raise ValueError(f"source coverage mismatch for shard {shard_number}: {cursor}")
        planned_shards.append({
            **shard, "shard_number": shard_number, "gguf_version": index["version"],
            "gguf_data_offset": index["data_offset"], "metadata": index["metadata"],
            "tensor_count": len(index["tensors"]), "regions": regions,
        })
    plan = {
        "schema": "aion.gguf-expert-frame-plan.v1",
        "status": "FROZEN_BEFORE_FULL_IMPORT",
        "source_schema": source.get("schema"),
        "source_revision": source.get("revision"),
        "representation": "expert-aligned independent Zstandard frames; shared tensors capped by size",
        "maximum_shared_frame_bytes": maximum_frame_bytes,
        "expert_frames": expert_frames,
        "other_frames": other_frames,
        "raw_bytes": sum(int(item["size"]) for item in source["shards"]),
        "shards": planned_shards,
    }
    plan["canonical_sha256"] = _canonical_hash(plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--header", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-shared-frame-mib", type=int, default=64)
    args = parser.parse_args()
    plan = build_plan(json.loads(args.source_manifest.read_text()), args.header,
                      args.maximum_shared_frame_mib * 1024 * 1024)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: plan[key] for key in
                      ("canonical_sha256", "raw_bytes", "expert_frames", "other_frames")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
