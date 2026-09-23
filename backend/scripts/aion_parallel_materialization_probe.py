#!/usr/bin/env python3
"""Probe parallel CPU page materialisation before unchanged MPS transfer.

This is deliberately a narrow mechanism experiment.  It reads real expert
weights from an SD-resident layer pack, compares lazy mmap-backed tensors with
parallel CPU clones, and then uses the ordinary PyTorch ``Tensor.to('mps')``
path in both conditions.  It does not replace or approximate model arithmetic.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import psutil
import torch
from safetensors import safe_open


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tensor_sha256(tensor: torch.Tensor) -> str:
    raw = tensor.detach().contiguous().view(torch.uint8).numpy().tobytes()
    return hashlib.sha256(raw).hexdigest()


def _summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    p95_index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return {
        "p50_seconds": statistics.median(values),
        "p95_seconds": ordered[p95_index],
    }


def _read(pack: Path, experts: tuple[int, ...]) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
    result = {}
    with safe_open(pack, framework="pt", device="cpu") as handle:
        for expert in experts:
            prefix = f"experts.{expert}"
            result[expert] = (
                handle.get_tensor(f"{prefix}.input_linear.weight"),
                handle.get_tensor(f"{prefix}.output_linear.weight"),
            )
    return result


def _clone_pair(pair: tuple[torch.Tensor, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    return tuple(value.clone(memory_format=torch.contiguous_format) for value in pair)  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--pack-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--experts", default="0,1,2,3,4,5,6,7")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()

    pack = args.pack.resolve()
    output = args.output.resolve()
    experts = tuple(int(value) for value in args.experts.split(","))
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if _sha256(pack) != args.pack_sha256:
        raise SystemExit("pack integrity failed")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    if args.workers < 1 or args.repetitions < 2 or not experts:
        raise SystemExit("invalid workers, repetitions or expert set")

    order = ("lazy", "parallel_materialized", "parallel_materialized", "lazy")
    trials: list[dict[str, Any]] = []
    expected_hashes: dict[str, str] | None = None
    peak_rss = psutil.Process().memory_info().rss
    for repetition in range(args.repetitions):
        for condition in order:
            torch.mps.empty_cache()
            started = time.perf_counter()
            weights = _read(pack, experts)
            mapping_seconds = time.perf_counter() - started

            materialize_started = time.perf_counter()
            if condition == "parallel_materialized":
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    pairs = list(executor.map(_clone_pair, weights.values()))
                weights = dict(zip(weights, pairs, strict=True))
            materialize_seconds = time.perf_counter() - materialize_started
            peak_rss = max(peak_rss, psutil.Process().memory_info().rss)

            transfer_started = time.perf_counter()
            device_weights = {
                expert: tuple(value.to(device="mps", dtype=torch.float16) for value in pair)
                for expert, pair in weights.items()
            }
            torch.mps.synchronize()
            transfer_seconds = time.perf_counter() - transfer_started

            # Copy back through the framework and hash every bit.  This is a
            # transfer-integrity gate, not a model-logit claim.
            hashes = {
                f"{expert}:{number}": _tensor_sha256(value.to("cpu"))
                for expert, pair in device_weights.items()
                for number, value in enumerate(pair)
            }
            if expected_hashes is None:
                expected_hashes = hashes
            exact = hashes == expected_hashes
            total_seconds = mapping_seconds + materialize_seconds + transfer_seconds
            trials.append({
                "repetition": repetition,
                "condition": condition,
                "mapping_seconds": mapping_seconds,
                "materialize_seconds": materialize_seconds,
                "transfer_seconds": transfer_seconds,
                "total_seconds": total_seconds,
                "exact_tensor_bits": exact,
            })
            del device_weights, weights

    summaries = {}
    for condition in ("lazy", "parallel_materialized"):
        selected = [trial for trial in trials if trial["condition"] == condition]
        summaries[condition] = {
            key: _summary([float(trial[key]) for trial in selected])
            for key in ("mapping_seconds", "materialize_seconds", "transfer_seconds", "total_seconds")
        }
    lazy = summaries["lazy"]["total_seconds"]["p50_seconds"]
    candidate = summaries["parallel_materialized"]["total_seconds"]["p50_seconds"]
    evidence: dict[str, Any] = {
        "schema_version": "aion.parallel-materialization-probe.v1",
        "pack": str(pack),
        "pack_sha256": args.pack_sha256,
        "experts": list(experts),
        "logical_bytes": sum(pair[0].numel() * pair[0].element_size() + pair[1].numel() * pair[1].element_size() for pair in _read(pack, experts).values()),
        "workers": args.workers,
        "repetitions": args.repetitions,
        "order": list(order),
        "conditions": {
            "lazy": "safetensors mmap tensors transferred by unchanged PyTorch MPS path",
            "parallel_materialized": "exact CPU clones produced concurrently, then transferred by the same PyTorch MPS path",
        },
        "summaries": summaries,
        "candidate_total_p50_change_percent": 100.0 * (candidate - lazy) / lazy,
        "all_transfer_bits_exact": all(trial["exact_tensor_bits"] for trial in trials),
        "peak_process_rss_bytes": peak_rss,
        "trials": trials,
        "claim_boundary": "Mechanism-only transfer test on real SD expert tensors; no model generation, token, logit, or end-to-end speed claim.",
    }
    evidence["canonical_sha256"] = hashlib.sha256(
        json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "canonical_sha256": evidence["canonical_sha256"],
        "all_transfer_bits_exact": evidence["all_transfer_bits_exact"],
        "candidate_total_p50_change_percent": evidence["candidate_total_p50_change_percent"],
        "summaries": summaries,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
