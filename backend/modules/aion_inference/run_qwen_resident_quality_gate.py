#!/usr/bin/env python3
"""Run the frozen structured semantic cohort against a resident local server."""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.request
from pathlib import Path
from typing import Any


def _normalise(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalise(item) for key, item in value.items()}
    return value


def _matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _matches(left, right) for left, right in zip(actual, expected)
        )
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=0.01)
    return _normalise(actual) == _normalise(expected)


def _parse_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(stripped)


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
    results = []
    for case in cohort["cases"]:
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
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
            elapsed = time.perf_counter() - started
            text = payload["choices"][0]["message"]["content"]
            parsed = _parse_json(text)
            passed = _matches(parsed, case["expected"])
            error = None
        except Exception as exc:  # evidence must preserve parse and transport failures
            elapsed = time.perf_counter() - started
            text = locals().get("text")
            parsed = None
            passed = False
            error = f"{type(exc).__name__}: {exc}"
            payload = locals().get("payload", {})
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        results.append(
            {
                "id": case["id"],
                "family": case["family"],
                "expected": case["expected"],
                "raw": text,
                "parsed": parsed,
                "pass": passed,
                "elapsed_seconds": elapsed,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "error": error,
            }
        )

    output = {
        "schema": "aion.qwen3moe.resident-structured-quality-gate.v1",
        "cohort_schema": cohort["schema_version"],
        "conditions": {"temperature": 0, "seed": 424242, "thinking": False},
        "passed": sum(item["pass"] for item in results),
        "total": len(results),
        "all_parseable": all(item["parsed"] is not None for item in results),
        "results": results,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["passed"] == output["total"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
