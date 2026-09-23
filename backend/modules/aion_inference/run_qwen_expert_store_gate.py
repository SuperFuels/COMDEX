"""Run the first bounded real-SD Qwen expert-address cache gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

try:
    from .qwen_expert_glyph_store import QwenExpertGlyphStore
except ImportError:  # Allows this self-contained SD diagnostic to run directly.
    from qwen_expert_glyph_store import QwenExpertGlyphStore


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, (95 * len(values) + 99) // 100 - 1)]


def run(manifest_path: Path, capacity_bytes: int) -> dict:
    shifts = (0, 4, 8, 0)
    token_times = []
    access_count = 0
    touched_bytes = 0
    with QwenExpertGlyphStore(manifest_path, capacity_bytes) as store:
        for shift in shifts:
            started = time.perf_counter()
            for layer in range(8):
                experts = [((layer * 7) + shift + index) % 128 for index in range(8)]
                values = store.get_layer_route(layer, experts)
                access_count += len(values)
                touched_bytes += sum(len(part) for expert in values for part in expert)
            token_times.append(time.perf_counter() - started)
        metrics = store.metrics()
    # Expert byte sizes vary slightly by layer in this quantized checkpoint.
    # The exact no-cache demand is therefore the sum of declared returned ranges,
    # not the model-wide mean expert size multiplied by access count.
    logical_bytes = touched_bytes
    report = {
        "schema": "aion.qwen3moe.expert-store-gate.v1",
        "manifest_path": str(manifest_path.resolve()),
        "capacity_bytes": capacity_bytes,
        "trace": {
            "kind": "synthetic-overlap-mechanism-gate",
            "layers": 8,
            "experts_per_layer": 8,
            "token_shifts": list(shifts),
            "expert_accesses": access_count,
        },
        "logical_bytes_without_cache": logical_bytes,
        "returned_bytes": touched_bytes,
        "physical_bytes": metrics["physical_bytes"],
        "physical_byte_reduction": 1 - metrics["physical_bytes"] / logical_bytes,
        "token_seconds": token_times,
        "token_seconds_p50": statistics.median(token_times),
        "token_seconds_p95_nearest_rank": _p95(token_times),
        "cache": metrics,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--capacity-mib", type=int, default=256)
    args = parser.parse_args()
    report = run(args.manifest, args.capacity_mib * 1024 * 1024)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
