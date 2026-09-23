from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveFactCheckBenchmark:
    """Repeatable, provider-independent quality and latency benchmark for public claims."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "live" / "benchmarks"
        self.latest_path = self.root / "latest.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        cases: Iterable[Dict[str, Any]],
        *,
        checker: Callable[[str], Dict[str, Any]],
        clock: Callable[[], float] = time.monotonic,
    ) -> Dict[str, Any]:
        results = []
        for raw in list(cases)[:50]:
            claim = " ".join(str(raw.get("claim") or "").split())[:500]
            expected = str(raw.get("expected_verdict") or "Unverifiable").title()
            if len(claim) < 8 or expected not in {"Supported", "Misleading", "False", "Disputed", "Unverifiable"}:
                continue
            started = clock()
            try:
                record = dict(checker(claim) or {})
                error = ""
            except Exception as exc:  # benchmark records failure; it does not hide it
                record = {}
                error = str(exc)[:200]
            elapsed_ms = max(0, int(round((clock() - started) * 1000)))
            sources = [item for item in list(record.get("sources") or record.get("items") or []) if isinstance(item, dict) and str(item.get("url") or "").startswith("https://")]
            observed = str(record.get("verdict") or "Unverifiable").title()
            result = {
                "case_id": str(raw.get("case_id") or f"case_{len(results)+1}")[:100],
                "claim": claim,
                "expected_verdict": expected,
                "observed_verdict": observed if observed in {"Supported", "Misleading", "False", "Disputed", "Unverifiable"} else "Unverifiable",
                "verdict_match": observed == expected,
                "latency_ms": elapsed_ms,
                "source_count": len(sources),
                "has_https_evidence": bool(sources),
                "provider": str(record.get("research_provider") or record.get("provider") or "unknown")[:120],
                "error": error,
            }
            result["result_hash"] = canonical_hash(result)
            results.append(result)
        latencies = [item["latency_ms"] for item in results]
        sorted_latency = sorted(latencies)
        p95_index = max(0, min(len(sorted_latency) - 1, int(round(0.95 * (len(sorted_latency) - 1))))) if sorted_latency else 0
        report: Dict[str, Any] = {
            "schema_version": "pilot.fact-check-benchmark.v1",
            "benchmark_id": f"benchmark_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "case_count": len(results),
            "metrics": {
                "verdict_accuracy": round(sum(1 for item in results if item["verdict_match"]) / len(results), 3) if results else 0.0,
                "https_evidence_coverage": round(sum(1 for item in results if item["has_https_evidence"]) / len(results), 3) if results else 0.0,
                "mean_latency_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
                "p95_latency_ms": sorted_latency[p95_index] if sorted_latency else 0,
                "error_count": sum(1 for item in results if item["error"]),
            },
            "results": results,
            "interpretation": {
                "benchmark_is_not_model_self_grading": True,
                "expected_verdicts_are_fixed_before_execution": True,
                "network_and_provider_failures_are_counted": True,
                "raw_provider_responses_retained": False,
            },
        }
        report["report_hash"] = canonical_hash(report)
        temporary = self.latest_path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(report))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.latest_path)
        return report

    def latest(self) -> Dict[str, Any] | None:
        if not self.latest_path.exists():
            return None
        try:
            value = json.loads(self.latest_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
