#!/usr/bin/env python3
"""Measure intrinsic zero/repetition structure in real packed MXFP4 experts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


def entropy(counts: np.ndarray) -> float:
    probabilities = counts[counts > 0] / counts.sum()
    return float(-(probabilities * np.log2(probabilities)).sum())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--activations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    captures = [json.loads(path.read_text())
                for path in sorted(args.activations.glob("position-*-layer-*.json"))]
    addresses = []
    for capture in captures:
        addresses.append((int(capture["layer"]), int(capture["route"][0])))
    addresses = list(dict.fromkeys(addresses))
    store = GptOssExpertFrameStore(args.manifest, 256 * 1024 * 1024)
    observations = []
    for layer, expert in addresses:
        value = store.get(layer, expert)
        for projection in ("gate", "up", "down"):
            packed = np.frombuffer(value[projection]["weight"], dtype=np.uint8)
            if packed.size % 17:
                raise RuntimeError("MXFP4 weight does not contain 17-byte blocks")
            blocks = packed.reshape(-1, 17)
            codes = blocks[:, 1:]
            nibble_counts = np.bincount(
                np.concatenate((codes & 15, codes >> 4)).reshape(-1), minlength=16)
            zero_codes = int(nibble_counts[0] + nibble_counts[8])
            zero_mask = ((codes & 15) == 0) | ((codes & 15) == 8)
            zero_mask &= (((codes >> 4) == 0) | ((codes >> 4) == 8))
            all_zero_blocks = int(zero_mask.all(axis=1).sum())
            scale_counts = np.bincount(blocks[:, 0], minlength=256)
            unique_blocks = len(np.unique(blocks, axis=0))
            observations.append({
                "layer": layer, "expert": expert, "projection": projection,
                "packed_bytes": int(packed.size), "blocks": int(len(blocks)),
                "zero_code_fraction": zero_codes / int(nibble_counts.sum()),
                "all_zero_block_fraction": all_zero_blocks / len(blocks),
                "nibble_entropy_bits": entropy(nibble_counts),
                "scale_entropy_bits": entropy(scale_counts),
                "unique_block_fraction": unique_blocks / len(blocks),
                "nibble_counts": nibble_counts.tolist(),
            })
    fields = ("zero_code_fraction", "all_zero_block_fraction",
              "nibble_entropy_bits", "scale_entropy_bits", "unique_block_fraction")
    summary = {}
    for field in fields:
        values = [observation[field] for observation in observations]
        summary[field] = {"minimum": min(values), "median": float(np.median(values)),
                          "maximum": max(values)}
    sparse = summary["zero_code_fraction"]["median"] >= .50 \
        or summary["all_zero_block_fraction"]["median"] >= .25
    repetitive = summary["unique_block_fraction"]["median"] <= .50
    report = {
        "schema": "aion.gptoss-120b-mxfp4-sparsity-analysis.v1",
        "status": "ADVANCE_EXACT_SPARSE_PACK" if sparse or repetitive else "STOP_EXACT_MXFP4_SPARSIFICATION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "sampled_layer_experts": [{"layer": layer, "expert": expert}
                                  for layer, expert in addresses],
        "observations": observations, "summary": summary,
        "promotion_gate": {"median_zero_code_fraction_at_least": .50,
                           "or_median_all_zero_block_fraction_at_least": .25,
                           "or_median_unique_block_fraction_at_most": .50},
        "warehouse_metrics": store.metrics(),
        "claim_boundary": (
            "The analysis samples the leading routed expert from 16 captured real states and "
            "all three packed matrices. MXFP4 blocks are interpreted as one shared-scale byte "
            "plus sixteen packed value bytes; codes 0 and 8 are the signed zero encodings. "
            "This is an intrinsic storage-structure gate, not a semantic or speed result."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "summary": summary,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
