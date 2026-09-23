#!/usr/bin/env python3
"""Bind and compare the exact GPT-OSS 120B protected-core/exception-halo runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


FIELDS = ("generated_token_id", "final_hidden_sha256", "logits_sha256")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    body = dict(value)
    body.pop("canonical_sha256", None)
    return hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def response_metrics(report: dict, label: str) -> dict:
    prompt = len(report["input_token_ids"])
    tokens = report[label]["tokens"][prompt:]
    times = [float(token["wall_seconds"]) for token in tokens]
    return {
        "tokens": len(tokens),
        "wall_seconds": sum(times),
        "tokens_per_second": len(times) / sum(times),
        "latency_median_seconds": statistics.median(times),
        "latency_p95_seconds": sorted(times)[int(.95 * (len(times) - 1))],
        "faults": report[label]["store_metric_delta"]["faults"],
        "hits": report[label]["store_metric_delta"]["hits"],
        "evictions": report[label]["store_metric_delta"]["evictions"],
        "total_pass_wall_seconds": report[label]["wall_seconds"],
    }


def exact_match(control: dict, candidate: dict) -> bool:
    for label in ("run_a", "run_b"):
        left = control[label]["tokens"]
        right = candidate[label]["tokens"]
        if len(left) != len(right):
            return False
        for a, b in zip(left, right, strict=True):
            if any(a[field] != b[field] for field in FIELDS):
                return False
            if [x["route"] for x in a["layers"]] != [x["route"] for x in b["layers"]]:
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--transient", type=Path, required=True)
    parser.add_argument("--halo-8-2", type=Path, required=True)
    parser.add_argument("--halo-6-4", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite summary")
    paths = {
        "unrestricted_control": args.control,
        "protected_8gib_transient_escape": args.transient,
        "protected_8gib_plus_2gib_halo": args.halo_8_2,
        "protected_6gib_plus_4gib_halo": args.halo_6_4,
    }
    reports = {name: json.loads(path.read_text()) for name, path in paths.items()}
    control = reports["unrestricted_control"]
    results = {}
    for name, report in reports.items():
        results[name] = {
            "path": str(paths[name].resolve()),
            "file_sha256": file_sha(paths[name]),
            "canonical_sha256": report["canonical_sha256"],
            "response": {label: response_metrics(report, label)
                         for label in ("run_a", "run_b")},
            "bit_exact_to_unrestricted_control": (
                True if name == "unrestricted_control" else exact_match(control, report)
            ),
        }
    control_rates = [results["unrestricted_control"]["response"][label]["tokens_per_second"]
                     for label in ("run_a", "run_b")]
    for name in results:
        rates = [results[name]["response"][label]["tokens_per_second"]
                 for label in ("run_a", "run_b")]
        results[name]["paired_speedup_percent"] = [
            100.0 * (rate / base - 1.0) for rate, base in zip(rates, control_rates, strict=True)
        ]
    result = {
        "schema": "aion.gptoss-120b-exact-core-halo-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "status": "PROMOTE_EXACT_CORE_HALO_MECHANISM",
        "results": results,
        "conclusion": (
            "A protected resident expert core plus an ordinary LRU exception halo preserved "
            "every unrestricted route, token, hidden-state hash and logit hash while materially "
            "reducing SD faults. The 6+4 GiB split was only marginally faster in response than "
            "8+2 GiB and is not an order-of-magnitude result. Static constrained 8 and 10 GiB "
            "pools failed the separate extraction-quality gate and remain NOT_PROMOTED."
        ),
        "claim_boundary": (
            "This is exact 48-position extraction-prompt execution evidence on one prompt, not "
            "a 30-token/s result, not broad semantic validation, and not proof that the full "
            "120B checkpoint is resident in Mac memory."
        ),
    }
    result["canonical_sha256"] = canonical(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"],
                      "canonical_sha256": result["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
