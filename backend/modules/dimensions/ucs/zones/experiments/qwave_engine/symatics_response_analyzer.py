from __future__ import annotations

"""
Symatics Response Analyzer
--------------------------
Reads one or more symatics_capture_*.jsonl files and measures whether the
external sensor channels separate symbolic states.

Outputs
- summary table to stdout
- backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_response_analysis.json
- backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_response_analysis.csv
"""

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List


OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)
JSON_OUT = OUTPUT_DIR / "symatics_response_analysis.json"
CSV_OUT = OUTPUT_DIR / "symatics_response_analysis.csv"


CHANNELS = [
    "pickup_voltage",
    "aux_adc_1",
    "aux_adc_2",
    "magnetometer_x",
    "magnetometer_y",
    "magnetometer_z",
    "temperature_c",
]


def _safe_mean(values: List[float]) -> float:
    return mean(values) if values else 0.0


def _safe_std(values: List[float]) -> float:
    return pstdev(values) if len(values) > 1 else 0.0


def _state_distance(a_mean: float, b_mean: float, a_std: float, b_std: float) -> float:
    """
    Simple separability score:
    distance between means normalized by pooled spread.
    """
    denom = max(1e-9, ((a_std + b_std) / 2.0))
    return abs(a_mean - b_mean) / denom


def load_capture(path: Path) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    if not rows:
        raise ValueError(f"No rows found in {path}")

    first = rows[0]
    expr = first["expression"]

    state = {
        "file": str(path),
        "name": expr["name"],
        "phi": float(expr["phi"]),
        "amplitude": float(expr["amplitude"]),
        "frequency": float(expr["frequency"]),
        "harmonics": expr["harmonics"],
        "rows": rows,
    }
    return state


def summarize_capture(capture: Dict[str, Any]) -> Dict[str, Any]:
    rows = capture["rows"]

    channel_stats: Dict[str, Dict[str, float]] = {}
    for channel in CHANNELS:
        vals = [
            float(row["external_sensors"][channel])
            for row in rows
            if channel in row["external_sensors"]
        ]
        channel_stats[channel] = {
            "mean": _safe_mean(vals),
            "std": _safe_std(vals),
            "min": min(vals) if vals else 0.0,
            "max": max(vals) if vals else 0.0,
        }

    internal_voltage = [
        float(row["internal_feedback"]["measured_voltage"])
        for row in rows
    ]
    internal_stability = [
        float(row["internal_feedback"]["stability_score"])
        for row in rows
    ]

    return {
        "file": capture["file"],
        "name": capture["name"],
        "phi": capture["phi"],
        "amplitude": capture["amplitude"],
        "frequency": capture["frequency"],
        "harmonics": capture["harmonics"],
        "ticks": len(rows),
        "internal_voltage_mean": _safe_mean(internal_voltage),
        "internal_voltage_std": _safe_std(internal_voltage),
        "internal_stability_mean": _safe_mean(internal_stability),
        "internal_stability_std": _safe_std(internal_stability),
        "channels": channel_stats,
    }


def pairwise_separation(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    for i in range(len(summaries)):
        for j in range(i + 1, len(summaries)):
            a = summaries[i]
            b = summaries[j]

            for channel in CHANNELS:
                a_stats = a["channels"][channel]
                b_stats = b["channels"][channel]
                sep = _state_distance(
                    a_stats["mean"],
                    b_stats["mean"],
                    a_stats["std"],
                    b_stats["std"],
                )

                out.append(
                    {
                        "state_a": a["name"],
                        "state_b": b["name"],
                        "channel": channel,
                        "mean_a": round(a_stats["mean"], 6),
                        "mean_b": round(b_stats["mean"], 6),
                        "std_a": round(a_stats["std"], 6),
                        "std_b": round(b_stats["std"], 6),
                        "separation_score": round(sep, 6),
                    }
                )

    out.sort(key=lambda x: x["separation_score"], reverse=True)
    return out


def infer_symbol_quality(summary: Dict[str, Any]) -> float:
    """
    Crude ranking for single-state quality.
    """
    pickup = summary["channels"]["pickup_voltage"]["mean"]
    pickup_std = summary["channels"]["pickup_voltage"]["std"]
    stability = summary["internal_stability_mean"]
    return round((stability * 2.0) + pickup - pickup_std, 6)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Symatics capture responses")
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit capture files. If omitted, all symatics_capture_*.jsonl files in outputs are used.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.files:
        paths = [Path(p) for p in args.files]
    else:
        paths = sorted(OUTPUT_DIR.glob("symatics_capture_*.jsonl"))

    if not paths:
        raise SystemExit("No capture files found.")

    captures = [load_capture(p) for p in paths]
    summaries = [summarize_capture(c) for c in captures]

    for s in summaries:
        s["symbol_quality_score"] = infer_symbol_quality(s)

    summaries.sort(key=lambda x: x["symbol_quality_score"], reverse=True)
    separations = pairwise_separation(summaries)

    with JSON_OUT.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "ok": True,
                "captures": summaries,
                "top_channel_separations": separations[:25],
            },
            f,
            indent=2,
        )

    with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "state_a",
                "state_b",
                "channel",
                "mean_a",
                "mean_b",
                "std_a",
                "std_b",
                "separation_score",
            ],
        )
        writer.writeheader()
        for row in separations:
            writer.writerow(row)

    print("=== Symatics Response Analysis ===")
    print("")
    print("Per-state summary:")
    for s in summaries:
        print(
            f"{s['name']} | phi={s['phi']:.6f} | harmonics={s['harmonics']} | "
            f"ticks={s['ticks']} | stability={s['internal_stability_mean']:.6f} | "
            f"pickup={s['channels']['pickup_voltage']['mean']:.6f} ± {s['channels']['pickup_voltage']['std']:.6f} | "
            f"quality={s['symbol_quality_score']:.6f}"
        )

    print("")
    print("Top channel separations:")
    for row in separations[:12]:
        print(
            f"{row['state_a']} vs {row['state_b']} | "
            f"{row['channel']} | sep={row['separation_score']:.6f} | "
            f"{row['mean_a']:.6f} vs {row['mean_b']:.6f}"
        )

    print("")
    print(f"JSON: {JSON_OUT}")
    print(f"CSV : {CSV_OUT}")


if __name__ == "__main__":
    main()