#!/usr/bin/env python3
"""Benchmark signed no-model rendering of supplier-payment controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from backend.modules.aion_inference import (
    render_supplier_payment_controls,
    verify_proof_receipt,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--cartridge", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--trust-anchors", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {
        "cartridge": args.cartridge.resolve(),
        "signature": args.signature.resolve(),
        "trust_anchors": args.trust_anchors.resolve(),
    }
    output = args.output.resolve()
    if args.iterations < 1:
        raise SystemExit("iterations must be positive")
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    elapsed = []
    answer_hashes = []
    receipts = []
    last = None
    for _ in range(args.iterations):
        started = time.perf_counter()
        last = render_supplier_payment_controls(
            cartridge_path=paths["cartridge"],
            signature_path=paths["signature"],
            trust_anchors_path=paths["trust_anchors"],
        )
        elapsed.append(time.perf_counter() - started)
        answer_hashes.append(hashlib.sha256(last.answer.encode()).hexdigest())
        receipts.append(str(last.proof_receipt["proof_receipt_sha256"]))
    assert last is not None
    lines = last.answer.splitlines()
    acceptance = {
        "all_answers_identical": len(set(answer_hashes)) == 1,
        "all_receipts_identical": len(set(receipts)) == 1,
        "receipt_valid": verify_proof_receipt(last.proof_receipt),
        "six_numbered_controls": (
            len(lines) == 6
            and all(line.startswith(f"{index}.") for index, line in enumerate(lines, start=1))
        ),
        "every_control_has_risk_and_human_evidence": all(
            "Risk prevented:" in line and "human evidence required:" in line
            for line in lines
        ),
        "model_call_avoided": not last.model_call_required,
        "payment_execution_never_allowed": not last.payment_execution_allowed,
    }
    report = {
        "schema_version": "aion.business-map-policy-economics.v1",
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {key: _sha256(value) for key, value in paths.items()},
        "iterations": args.iterations,
        "latency": {
            "median_seconds": statistics.median(elapsed),
            "p95_seconds_nearest_rank": _p95(elapsed),
            "minimum_seconds": min(elapsed),
            "maximum_seconds": max(elapsed),
        },
        "answer_sha256": answer_hashes[0],
        "proof_receipt_sha256": receipts[0],
        "answer": last.answer,
        "acceptance": acceptance,
        "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": (
            "Synthetic informational policy rendering from an operator-approved prototype "
            "cartridge. It proves signed deterministic retrieval and formatting, not external "
            "policy correctness, production approval, evidence authenticity or payment authority."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "latency": report["latency"],
        "acceptance": acceptance,
        "result": report["result"],
    }, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
