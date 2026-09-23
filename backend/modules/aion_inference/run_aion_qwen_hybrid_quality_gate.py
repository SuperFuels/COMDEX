#!/usr/bin/env python3
"""Evaluate verified AION routes with resident Qwen as the guarded fallback."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from backend.modules.aion_inference import AdaptiveInferenceRuntime
from backend.modules.aion_inference.run_qwen_resident_quality_gate import (
    _matches,
    _parse_json,
)


def _coerce_verified(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _coerce_verified(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_verified(item) for item in value]
    if isinstance(value, str):
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8899/v1/chat/completions")
    parser.add_argument(
        "--cohort",
        type=Path,
        default=Path(__file__).with_name("evals") / "int8_general_semantic_tasks.v1.json",
    )
    args = parser.parse_args()
    cohort = json.loads(args.cohort.read_text())

    with tempfile.TemporaryDirectory(prefix="aion-qwen-hybrid-") as directory:
        root = Path(directory)
        runtime = AdaptiveInferenceRuntime(
            replay_path=root / "replay.sqlite3",
            trace_path=root / "trace.jsonl",
        )
        results = []
        for case in cohort["cases"]:
            started = time.perf_counter()
            routed = runtime.route(case["prompt"])
            route_latency = time.perf_counter() - started
            if not routed.model_call_required:
                parsed = _coerce_verified(dict(routed.structured_result or {}))
                route = routed.route
                model_calls = 0
                completion_tokens = 0
                model_latency = 0.0
                raw = routed.answer
            else:
                body = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "Follow the requested schema exactly. Return only valid JSON and no explanation.",
                        },
                        {"role": "user", "content": case["prompt"]},
                    ],
                    "temperature": 0,
                    "seed": 424242,
                    "max_tokens": 128,
                    "chat_template_kwargs": {"enable_thinking": False},
                }
                request = urllib.request.Request(
                    args.url,
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"},
                )
                model_started = time.perf_counter()
                with urllib.request.urlopen(request, timeout=120) as response:
                    payload = json.loads(response.read())
                model_latency = time.perf_counter() - model_started
                raw = payload["choices"][0]["message"]["content"]
                parsed = _parse_json(raw)
                route = "resident_qwen_fallback"
                model_calls = 1
                completion_tokens = payload.get("usage", {}).get("completion_tokens", 0)
            results.append(
                {
                    "id": case["id"],
                    "family": case["family"],
                    "route": route,
                    "pass": _matches(parsed, case["expected"]),
                    "expected": case["expected"],
                    "parsed": parsed,
                    "raw": raw,
                    "model_calls": model_calls,
                    "completion_tokens": completion_tokens,
                    "route_latency_seconds": route_latency,
                    "model_latency_seconds": model_latency,
                    "total_latency_seconds": route_latency + model_latency,
                }
            )

    output = {
        "schema": "aion.qwen3moe.hybrid-structured-quality-gate.v1",
        "cohort_schema": cohort["schema_version"],
        "passed": sum(item["pass"] for item in results),
        "total": len(results),
        "model_calls": sum(item["model_calls"] for item in results),
        "model_tokens": sum(item["completion_tokens"] for item in results),
        "verified_tasks": sum(item["model_calls"] == 0 for item in results),
        "results": results,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["passed"] == output["total"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
