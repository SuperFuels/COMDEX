from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path

# Keep this runner as quiet as possible before importing repo modules.
os.environ.setdefault("SQI_FACTOR_QUIET", "1")
os.environ.setdefault("AION_HEARTBEAT_DISABLED", "1")
os.environ.setdefault("TESSARIS_DISABLE_HEARTBEAT", "1")
os.environ.setdefault("TESSARIS_QUIET_IMPORTS", "1")


def _quiet_import_factor_module():
    """
    Import factor module while swallowing noisy package-level stdout/stderr
    from the wider backend runtime.
    """
    stdout = io.StringIO()
    stderr = io.StringIO()

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        from backend.modules.sqi.factor.sqi_prime_factorizer import (
            benchmark,
            run_large_benchmark_table,
            sqi_factor_once,
        )

    return benchmark, run_large_benchmark_table, sqi_factor_once


benchmark, run_large_benchmark_table, sqi_factor_once = _quiet_import_factor_module()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SQI adaptive prime factor search CLI"
    )
    parser.add_argument(
        "n",
        nargs="?",
        type=int,
        help="Integer to factor. Omit when using --table.",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Run the larger benchmark table.",
    )
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Disable JSONL trace artifact output.",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Disable dashboard JSON artifact output.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run full benchmark comparison for one integer.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Optional output JSON path.",
    )

    args = parser.parse_args()

    if args.table:
        rows = run_large_benchmark_table()
        payload = {
            "mode": "table",
            "rows": rows,
            "benchmark_path": "benchmarks/sqi_prime_factor_benchmark_v2.json",
            "dashboard_path": "benchmarks/sqi_prime_factor_dashboard_v2.json",
        }
    else:
        if args.n is None:
            raise SystemExit("Provide an integer N or use --table.")

        if args.benchmark:
            payload = {
                "mode": "benchmark",
                "result": benchmark(args.n),
            }
        else:
            result = sqi_factor_once(
                args.n,
                trace_jsonl=not args.no_trace,
                dashboard_json=not args.no_dashboard,
            )
            payload = {
                "mode": "factor",
                "n": result.n,
                "factor": result.found_factor,
                "cofactor": result.cofactor,
                "method": result.method,
                "checked": result.checked,
                "branches_generated": result.branches_generated,
                "branches_pruned": result.branches_pruned,
                "elapsed_ms": round(result.elapsed_ms, 4),
                "trace_path": result.trace_path,
                "dashboard_path": result.dashboard_path,
                "trace_tail": result.trace[-5:],
            }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    if payload["mode"] == "factor":
        print("=== SQI Factor Result ===")
        print(f"N:                  {payload['n']}")
        print(f"factor:             {payload['factor']}")
        print(f"cofactor:           {payload['cofactor']}")
        print(f"method:             {payload['method']}")
        print(f"checked:            {payload['checked']}")
        print(f"branches generated: {payload['branches_generated']}")
        print(f"branches pruned:    {payload['branches_pruned']}")
        print(f"elapsed ms:         {payload['elapsed_ms']}")
        print(f"trace:              {payload['trace_path']}")
        print(f"dashboard:          {payload['dashboard_path']}")
    elif payload["mode"] == "benchmark":
        result = payload["result"]
        print("=== SQI Factor Benchmark ===")
        print(json.dumps({
            "n": result["n"],
            "sqi": result["sqi"],
            "naive": result["naive"],
            "wheel": result["wheel"],
            "fermat_only": result["fermat_only"],
            "pollard_only": result["pollard_only"],
            "brent_only": result["brent_only"],
            "full_factorization": result["full_factorization"],
        }, indent=2, sort_keys=True))
    else:
        print("=== SQI Factor Benchmark Table ===")
        print(f"rows: {len(payload['rows'])}")
        print(f"benchmark: {payload['benchmark_path']}")
        print(f"dashboard: {payload['dashboard_path']}")


if __name__ == "__main__":
    main()
