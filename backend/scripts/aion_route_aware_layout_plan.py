#!/usr/bin/env python3
"""Build a signed, deterministic physical expert-layout plan from route evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from typing import Any, Iterable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_order(path: Path) -> tuple[int, ...]:
    with path.open("rb") as handle:
        header_bytes = struct.unpack("<Q", handle.read(8))[0]
        header = json.loads(handle.read(header_bytes))
    offsets = {}
    for name, value in header.items():
        if name == "__metadata__" or not name.endswith(".input_linear.weight"):
            continue
        expert = int(name.split(".")[1])
        offsets[expert] = int(value["data_offsets"][0])
    return tuple(expert for expert, _ in sorted(offsets.items(), key=lambda item: item[1]))


def _objective(order: tuple[int, ...], pairs: Counter[tuple[int, int]]) -> int:
    positions = {expert: index for index, expert in enumerate(order)}
    return sum(weight * abs(positions[a] - positions[b]) for (a, b), weight in pairs.items())


def _improve(start: tuple[int, ...], pairs: Counter[tuple[int, int]]) -> tuple[int, ...]:
    current = list(start)
    current_score = _objective(current, pairs)
    while True:
        positions = {expert: index for index, expert in enumerate(current)}
        best_swap: tuple[int, int] | None = None
        best_delta = 0
        for left in range(len(current) - 1):
            for right in range(left + 1, len(current)):
                first, second = current[left], current[right]
                delta = 0
                for other in current:
                    if other in (first, second):
                        continue
                    position = positions[other]
                    first_pair = tuple(sorted((first, other)))
                    second_pair = tuple(sorted((second, other)))
                    delta += pairs[first_pair] * (
                        abs(right - position) - abs(left - position)
                    )
                    delta += pairs[second_pair] * (
                        abs(left - position) - abs(right - position)
                    )
                if delta < best_delta or (
                    delta == best_delta and delta < 0 and
                    (best_swap is None or (left, right) < best_swap)
                ):
                    best_swap, best_delta = (left, right), delta
        if best_swap is None:
            return tuple(current)
        left, right = best_swap
        current[left], current[right] = current[right], current[left]
        current_score += best_delta


def _route_metrics(order: tuple[int, ...], routes: Iterable[tuple[int, ...]]) -> dict[str, float]:
    positions = {expert: index for index, expert in enumerate(order)}
    spans, runs = [], []
    for route in routes:
        selected = sorted({positions[expert] for expert in route})
        if not selected:
            continue
        spans.append(selected[-1] - selected[0] + 1)
        runs.append(1 + sum(b != a + 1 for a, b in zip(selected, selected[1:])))
    return {
        "mean_expert_span": sum(spans) / len(spans),
        "mean_contiguous_runs": sum(runs) / len(runs),
        "route_count": float(len(spans)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    manifest_path = args.pack_manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    observations = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((args.route_corpus.resolve() / "objects").glob("*.json"))
    ]
    if not observations or len(manifest["layers"]) != 32:
        raise SystemExit("expected route observations and 32 layer packs")
    manifest_sha = _sha256(manifest_path)
    if any(item["bindings"]["pack_manifest_sha256"] != manifest_sha for item in observations):
        raise SystemExit("route corpus is not bound to the selected pack manifest")

    layers: list[dict[str, Any]] = []
    for layer, pack in enumerate(manifest["layers"]):
        routes: list[tuple[int, ...]] = []
        frequency: Counter[int] = Counter()
        pairs: Counter[tuple[int, int]] = Counter()
        for observation in observations:
            for batch in observation["route_batches_by_layer"][layer]:
                for raw_route in batch:
                    route = tuple(sorted(set(int(value) for value in raw_route)))
                    routes.append(route)
                    frequency.update(route)
                    for index, first in enumerate(route):
                        for second in route[index + 1:]:
                            pairs[first, second] += 1
        source = _source_order(Path(pack["path"]))
        numeric = tuple(range(40))
        by_frequency = tuple(sorted(range(40), key=lambda value: (-frequency[value], value)))
        candidates = tuple(_improve(start, pairs) for start in (source, numeric, by_frequency))
        selected = min(candidates, key=lambda order: (_objective(order, pairs), order))
        source_score = _objective(source, pairs)
        selected_score = _objective(selected, pairs)
        source_metrics = _route_metrics(source, routes)
        candidate_metrics = _route_metrics(selected, routes)
        layers.append({
            "layer": layer,
            "source_pack": str(Path(pack["path"]).resolve()),
            "source_pack_sha256": pack["sha256"],
            "source_order": list(source),
            "candidate_order": list(selected),
            "weighted_pair_distance_source": source_score,
            "weighted_pair_distance_candidate": selected_score,
            "weighted_pair_distance_reduction_percent": 100.0 * (1.0 - selected_score / source_score),
            "source_route_metrics": source_metrics,
            "candidate_route_metrics": candidate_metrics,
        })

    source_total = sum(layer["weighted_pair_distance_source"] for layer in layers)
    candidate_total = sum(layer["weighted_pair_distance_candidate"] for layer in layers)
    report: dict[str, Any] = {
        "schema_version": "aion.route-aware-physical-layout-plan.v1",
        "route_corpus": str(args.route_corpus.resolve()),
        "observation_sha256s": sorted(item["observation_sha256"] for item in observations),
        "source_pack_manifest": str(manifest_path),
        "source_pack_manifest_sha256": manifest_sha,
        "optimization": "deterministic multi-start pair-swap minimization of corpus-weighted physical expert distance",
        "layers": layers,
        "aggregate": {
            "weighted_pair_distance_source": source_total,
            "weighted_pair_distance_candidate": candidate_total,
            "weighted_pair_distance_reduction_percent": 100.0 * (1.0 - candidate_total / source_total),
            "mean_source_route_span": sum(layer["source_route_metrics"]["mean_expert_span"] for layer in layers) / 32,
            "mean_candidate_route_span": sum(layer["candidate_route_metrics"]["mean_expert_span"] for layer in layers) / 32,
            "mean_source_contiguous_runs": sum(layer["source_route_metrics"]["mean_contiguous_runs"] for layer in layers) / 32,
            "mean_candidate_contiguous_runs": sum(layer["candidate_route_metrics"]["mean_contiguous_runs"] for layer in layers) / 32,
        },
        "claim_boundary": "This is a corpus-bound physical-layout plan and locality simulation. It does not claim SD latency or model-throughput improvement until exact reordered packs are built and tested head-to-head.",
    }
    report["plan_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "plan_sha256": report["plan_sha256"], "aggregate": report["aggregate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
