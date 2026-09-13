"""Reproducible baseline runner for the Qwen3.8 27B Local Pro candidate.

This deliberately measures the standard llama.cpp Metal path before any
Tessaris-specific caching or packaging optimisation is considered.  It records
cold and warm generation separately and never promotes a package to release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any

EXPECTED_Q3_BYTES = 13_146_393_504
DEFAULT_RUNTIME = "/opt/homebrew/bin/llama-cli"
WORKLOADS = Path(__file__).with_name("workloads.v1.json")
TIMING_RE = re.compile(r"eval time\s*=\s*([0-9.]+)\s*ms\s*/\s*([0-9]+)\s*tokens\s*\(([0-9.]+)\s*tokens per second\)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cases(limit: int | None) -> list[dict[str, Any]]:
    document = json.loads(WORKLOADS.read_text(encoding="utf-8"))
    cases = list(document["cases"])
    return cases if limit is None else cases[:limit]


def quality(case: dict[str, Any], response: str) -> dict[str, str]:
    check = dict(case.get("quality_check") or {})
    kind = check.get("type", "human_review")
    if kind == "contains_all":
        missing = [str(value) for value in check.get("values", []) if str(value).lower() not in response.lower()]
        return {"status": "pass" if not missing else "fail", "detail": "" if not missing else f"missing:{','.join(missing)}"}
    if kind == "regex":
        matched = bool(re.search(str(check.get("pattern", "")), response, re.IGNORECASE))
        return {"status": "pass" if matched else "fail", "detail": "" if matched else "pattern_not_found"}
    return {"status": "review_required", "detail": "human_review"}


def run_case(runtime: str, model: Path, case: dict[str, Any], threads: int, phase: str) -> dict[str, Any]:
    command = [
        runtime, "-m", str(model), "--single-turn", "--no-display-prompt", "--color", "off",
        "--reasoning", "off", "--temp", "0", "--seed", "42", "--ctx-size", "4096",
        "--gpu-layers", "999", "--flash-attn", "auto", "--threads", str(threads),
        "--threads-batch", str(threads), "--predict", str(case["max_output_tokens"]),
        "--prompt", str(case["prompt"]),
    ]
    if phase == "cold":
        command.append("--no-warmup")
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=900)
    wall = time.perf_counter() - started
    timing = TIMING_RE.search(completed.stderr)
    response = completed.stdout.strip()
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "command": command,
        "exit_code": completed.returncode,
        "wall_seconds": round(wall, 3),
        "response": response,
        "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
        "quality": quality(case, response),
        "evaluation": ({"milliseconds": float(timing.group(1)), "tokens": int(timing.group(2)), "tokens_per_second": float(timing.group(3))} if timing else None),
        "stderr": completed.stderr[-12000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", choices=("cold", "warm"), required=True)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--runtime", default=DEFAULT_RUNTIME)
    args = parser.parse_args()
    if not args.model.is_file():
        raise SystemExit(f"model_missing:{args.model}")
    size = args.model.stat().st_size
    if size != EXPECTED_Q3_BYTES:
        raise SystemExit(f"model_incomplete_or_unexpected_size:observed={size}:expected={EXPECTED_Q3_BYTES}")
    if not Path(args.runtime).is_file():
        raise SystemExit(f"runtime_missing:{args.runtime}")
    cases = load_cases(args.limit)
    started = datetime.now(timezone.utc).isoformat()
    results = [run_case(args.runtime, args.model, case, args.threads, args.phase) for case in cases]
    rates = [result["evaluation"]["tokens_per_second"] for result in results if result["evaluation"]]
    report = {
        "schema_version": "aion.qwen3-8-local-pro-baseline.v1",
        "candidate": "unsloth/Qwen3.8-27B-GGUF:Qwen3.8-27B-UD-Q3_K_XL.gguf",
        "release_status": "benchmark_only_not_selectable",
        "phase": args.phase,
        "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.platform(), "machine": platform.machine(), "python": sys.version},
        "runtime": {"path": args.runtime, "sha256": sha256(Path(args.runtime)), "threads": args.threads, "gpu_layers": 999, "flash_attention": "auto", "context_tokens": 4096, "reasoning": "off"},
        "model": {"path": str(args.model), "bytes": size, "sha256": sha256(args.model)},
        "workloads": {"path": str(WORKLOADS), "sha256": sha256(WORKLOADS), "case_count": len(cases)},
        "summary": {"measured_cases": len(rates), "median_tokens_per_second": sorted(rates)[len(rates)//2] if rates else None, "minimum_tokens_per_second": min(rates) if rates else None, "maximum_tokens_per_second": max(rates) if rates else None},
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
