#!/usr/bin/env python3
"""Compile a hash-bound, original-weight GPT-OSS constrained expert pool."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _canonical(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-report", action="append", type=Path, required=True)
    parser.add_argument("--experts-per-layer", type=int, default=16)
    parser.add_argument("--max-tokens-per-report", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite expert pool")
    if args.experts_per_layer < 4 or args.experts_per_layer > 128:
        raise SystemExit("experts-per-layer must be between 4 and 128")
    counts = [collections.Counter() for _ in range(36)]
    sources = []
    for path in args.route_report:
        report = json.loads(path.read_text())
        if (report.get("status") != "PASSED"
                or report.get("final_hidden_and_logits_bitwise_repeatable") is not True):
            raise SystemExit(f"route report is not exact and passed: {path}")
        tokens = report["run_a"]["tokens"]
        if args.max_tokens_per_report is not None:
            if args.max_tokens_per_report < 1:
                raise SystemExit("max-tokens-per-report must be positive")
            tokens = tokens[:args.max_tokens_per_report]
        for token in tokens:
            if len(token["layers"]) != 36:
                raise SystemExit(f"incomplete layer coverage: {path}")
            for layer in range(36):
                counts[layer].update(token["layers"][layer]["route"])
        sources.append({
            "path": str(path.resolve()),
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "canonical_sha256": report.get("canonical_sha256"),
            "available_tokens": len(report["run_a"]["tokens"]),
            "tokens_used": len(tokens),
        })
    layers = {}
    for layer, counter in enumerate(counts):
        ordered = [expert for expert, _ in sorted(
            counter.items(), key=lambda item: (-item[1], item[0]))]
        if len(ordered) < args.experts_per_layer:
            raise SystemExit(f"layer {layer} has only {len(ordered)} observed experts")
        layers[str(layer)] = ordered[:args.experts_per_layer]
    result = {
        "schema": "aion.gptoss-120b-constrained-expert-pool.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "quality_track": True,
        "selection": "per-layer observed frequency, stable expert-id tie break",
        "experts_per_layer": args.experts_per_layer,
        "total_layer_experts": 36 * args.experts_per_layer,
        "sources": sources,
        "layers": layers,
        "claim_boundary": (
            "Every retained weight is an original GPT-OSS 120B expert weight, but routing is "
            "constrained to this pool. This is a changed-model quality track and is not exact "
            "full-model inference."
        ),
    }
    result["canonical_sha256"] = _canonical(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"experts_per_layer": args.experts_per_layer,
                      "total_layer_experts": result["total_layer_experts"],
                      "canonical_sha256": result["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
