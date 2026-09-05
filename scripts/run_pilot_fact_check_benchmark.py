from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.aion_fabric.fact_check_benchmark import LiveFactCheckBenchmark
from backend.modules.aion_fabric.live_news import LiveNewsIntelligence
from backend.modules.aion_fabric.research import AionTVResearch


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Pilot's repeatable public live-news fact-check benchmark")
    parser.add_argument("--runtime-dir", default=".runtime/aion_fabric")
    parser.add_argument("--cases", default="docs/aion/fixtures/PILOT_LIVE_FACT_CHECK_BENCHMARK_CASES.json")
    args = parser.parse_args()
    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    research = AionTVResearch(args.runtime_dir)
    compiler = LiveNewsIntelligence(args.runtime_dir)

    def check(claim: str):
        result = research.search(claim, mode="fact_check")
        return compiler.compile(
            live_context={"recent_statement": claim},
            research=result,
            screen_understanding=None,
            latency_ms=int(result.get("latency_ms") or 0),
        )

    report = LiveFactCheckBenchmark(args.runtime_dir).run(cases, checker=check)
    print(json.dumps(report, indent=2))
    return 0 if report["case_count"] and not report["metrics"]["error_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
