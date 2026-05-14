from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("mode"))].append(row)

    summary_rows: List[Dict[str, Any]] = []

    for mode, grp in grouped.items():
        n = len(grp)
        coherence = [_safe_float(r.get("coherence")) for r in grp]
        entropy = [_safe_float(r.get("entropy")) for r in grp]
        delta_phi = [_safe_float(r.get("delta_phi")) for r in grp]
        reward = [_safe_float(r.get("reward")) for r in grp]
        field_quality = [_safe_float(r.get("field_quality")) for r in grp]
        stability = [_safe_float(r.get("stability_score")) for r in grp]

        hold_current_pct = 100.0 * sum(
            1 for r in grp if r.get("field_operator_mode") == "hold_current"
        ) / n if n else 0.0

        constructive_pct = 100.0 * sum(
            1 for r in grp if str(r.get("observed_regime") or "").lower() == "constructive"
        ) / n if n else 0.0

        summary_rows.append(
            {
                "mode": mode,
                "cycles": n,
                "mean_coherence": _mean(coherence),
                "mean_entropy": _mean(entropy),
                "mean_delta_phi": _mean(delta_phi),
                "mean_reward": _mean(reward),
                "mean_field_quality": _mean(field_quality),
                "mean_stability_score": _mean(stability),
                "hold_current_pct": hold_current_pct,
                "constructive_pct": constructive_pct,
            }
        )

    return sorted(summary_rows, key=lambda x: x["mode"])


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: List[Dict[str, Any]]) -> None:
    baseline = next((r for r in rows if r["mode"] == "baseline_hold"), None)
    proposed = next((r for r in rows if r["mode"] == "apply_proposed"), None)
    bad = next((r for r in rows if r["mode"] == "bad_perturbation"), None)

    lines: List[str] = []
    lines.append("# Field Control Report")
    lines.append("")
    lines.append("| mode | cycles | mean_coherence | mean_entropy | mean_delta_phi | mean_reward | mean_field_quality | mean_stability_score | hold_current_pct | constructive_pct |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for r in rows:
        lines.append(
            f"| {r['mode']} | {r['cycles']} | "
            f"{r['mean_coherence']:.6f} | {r['mean_entropy']:.6f} | {r['mean_delta_phi']:.6f} | "
            f"{r['mean_reward']:.6f} | {r['mean_field_quality']:.6f} | {r['mean_stability_score']:.6f} | "
            f"{r['hold_current_pct']:.2f} | {r['constructive_pct']:.2f} |"
        )

    lines.append("")
    lines.append("## Comparison")
    lines.append("")

    if baseline and proposed:
        lines.append(
            f"- apply_proposed vs baseline_hold: "
            f"Δfield_quality = {proposed['mean_field_quality'] - baseline['mean_field_quality']:+.6f}"
        )
        lines.append(
            f"- apply_proposed vs baseline_hold: "
            f"Δreward = {proposed['mean_reward'] - baseline['mean_reward']:+.6f}"
        )

    if baseline and bad:
        lines.append(
            f"- bad_perturbation vs baseline_hold: "
            f"Δfield_quality = {bad['mean_field_quality'] - baseline['mean_field_quality']:+.6f}"
        )
        lines.append(
            f"- bad_perturbation vs baseline_hold: "
            f"Δreward = {bad['mean_reward'] - baseline['mean_reward']:+.6f}"
        )

    lines.append("")
    lines.append("## Acceptance Heuristic")
    lines.append("")
    lines.append("- Good sign: `apply_proposed` improves mean_field_quality and/or mean_reward over `baseline_hold`.")
    lines.append("- Good sign: `bad_perturbation` degrades mean_field_quality relative to `baseline_hold`.")
    lines.append("- Good sign: stable regimes produce higher `hold_current_pct` rather than unnecessary oscillation.")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build field-control report")
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        default=Path(".runtime/aion_field_control/field_control_runs.jsonl"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".runtime/aion_field_control"),
    )
    args = parser.parse_args()

    rows = load_jsonl(args.input_jsonl)
    summary_rows = build_summary(rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = args.output_dir / "field_control_summary.csv"
    md_path = args.output_dir / "field_control_report.md"
    json_path = args.output_dir / "field_control_summary.json"

    write_csv(csv_path, summary_rows)
    write_markdown(md_path, summary_rows)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary_rows, f, ensure_ascii=False, indent=2)

    print(f"Wrote:\n  {csv_path}\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()