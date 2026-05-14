from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _phi_of(row: dict[str, Any]) -> float:
    return float(row.get("phi_hint", row.get("phi", math.nan)))


def _pickup_of(row: dict[str, Any]) -> float:
    if "pickup" in row:
        return float(row["pickup"])
    return float(row.get("pickup_mean", 0.0))


def _group_mean_by_phi(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[float, list[float]] = {}
    for row in rows:
        phi = _phi_of(row)
        pickup = _pickup_of(row)
        grouped.setdefault(phi, []).append(pickup)

    out: list[dict[str, Any]] = []
    for phi in sorted(grouped):
        vals = np.asarray(grouped[phi], dtype=float)
        out.append(
            {
                "phi": float(phi),
                "n": int(vals.size),
                "pickup_mean": float(np.mean(vals)),
                "pickup_std": float(np.std(vals)),
                "cos2_model": float(math.cos(phi / 2.0) ** 2),
            }
        )
    return out


def _normalize(values: list[float]) -> list[float]:
    arr = np.asarray(values, dtype=float)
    vmin = float(np.min(arr))
    vmax = float(np.max(arr))
    if vmax <= vmin:
        return [0.0 for _ in values]
    return [float((x - vmin) / (vmax - vmin)) for x in arr]


def _find_null_point(points: list[dict[str, Any]]) -> dict[str, Any]:
    return min(points, key=lambda p: p["pickup_mean"])


def _symmetry_error(points: list[dict[str, Any]], center_phi: float, tol: float = 1e-6) -> float:
    by_phi = {round(p["phi"], 9): p for p in points}
    errs: list[float] = []

    for p in points:
        phi = p["phi"]
        reflected = 2.0 * center_phi - phi
        key = round(reflected, 9)
        if key in by_phi:
            q = by_phi[key]
            errs.append(abs(p["pickup_norm"] - q["pickup_norm"]))

    if not errs:
        return float("inf")
    return float(np.mean(errs))


def _rmse(points: list[dict[str, Any]]) -> float:
    errs = [(p["pickup_norm"] - p["cos2_model"]) ** 2 for p in points]
    return float(math.sqrt(sum(errs) / len(errs))) if errs else float("inf")


def _classify_state(phi: float, width: float) -> str:
    phi_mod = phi % (2.0 * math.pi)

    def circ_dist(a: float, b: float) -> float:
        d = abs(a - b) % (2.0 * math.pi)
        return min(d, 2.0 * math.pi - d)

    if circ_dist(phi_mod, math.pi) <= width:
        return "S4_destructive"
    if circ_dist(phi_mod, 0.0) <= width or circ_dist(phi_mod, 2.0 * math.pi) <= width:
        return "S1_constructive"
    return "S2_intermediate"


def run(args: argparse.Namespace) -> None:
    rows = _load_jsonl(Path(args.input))
    points = _group_mean_by_phi(rows)

    norms = _normalize([p["pickup_mean"] for p in points])
    for p, norm in zip(points, norms):
        p["pickup_norm"] = norm
        p["abs_err"] = abs(p["pickup_norm"] - p["cos2_model"])
        p["predicted_state"] = _classify_state(p["phi"], args.state_width)

    null_point = _find_null_point(points)
    rmse = _rmse(points)
    sym_err = _symmetry_error(points, null_point["phi"])
    distance_to_pi = abs(null_point["phi"] - math.pi)

    passes = {
        "null_near_pi": distance_to_pi <= args.max_distance_to_pi,
        "rmse_within_threshold": rmse <= args.max_rmse,
        "symmetry_within_threshold": sym_err <= args.max_symmetry_error,
    }
    overall_pass = all(passes.values())

    payload = {
        "input": str(args.input),
        "point_count": len(points),
        "null_point": {
            "phi": null_point["phi"],
            "pickup_mean": null_point["pickup_mean"],
            "pickup_norm": null_point["pickup_norm"],
            "distance_to_pi": distance_to_pi,
        },
        "metrics": {
            "rmse_vs_cos2": rmse,
            "symmetry_error": sym_err,
        },
        "thresholds": {
            "max_distance_to_pi": args.max_distance_to_pi,
            "max_rmse": args.max_rmse,
            "max_symmetry_error": args.max_symmetry_error,
        },
        "passes": passes,
        "overall_pass": overall_pass,
        "points": points,
    }

    print("\n=== INTERFERENCE VERIFICATION ===\n")
    print(f"input              : {args.input}")
    print(f"points             : {len(points)}")
    print(f"null phi           : {null_point['phi']:.9f}")
    print(f"distance to pi     : {distance_to_pi:.9e}")
    print(f"rmse vs cos^2      : {rmse:.9f}")
    print(f"symmetry error     : {sym_err:.9f}")
    print(f"overall pass       : {overall_pass}")
    print()

    print("phi, pickup_mean, pickup_norm, cos2_model, abs_err, state")
    for p in points:
        print(
            f"{p['phi']:.6f}, "
            f"{p['pickup_mean']:.9f}, "
            f"{p['pickup_norm']:.9f}, "
            f"{p['cos2_model']:.9f}, "
            f"{p['abs_err']:.9f}, "
            f"{p['predicted_state']}"
        )

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote JSON: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Verify Symatics broad phase sweep against cos^2(phi/2).")
    ap.add_argument("--input", required=True, help="Path to capture sweep JSONL")
    ap.add_argument(
        "--json-out",
        default="backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/interference_verification_latest.json",
    )
    ap.add_argument("--max-distance-to-pi", type=float, default=0.35)
    ap.add_argument("--max-rmse", type=float, default=0.55)
    ap.add_argument("--max-symmetry-error", type=float, default=0.08)
    ap.add_argument(
        "--state-width",
        type=float,
        default=0.35,
        help="Angular half-width for classifying S1/S4 regions.",
    )
    run(ap.parse_args())