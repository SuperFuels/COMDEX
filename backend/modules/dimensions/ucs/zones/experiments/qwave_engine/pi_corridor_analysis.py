from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

TWO_PI = 2.0 * math.pi
PI = math.pi
PHI_KEY_DECIMALS = 12


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _wrap_phi(phi: float) -> float:
    return float(phi) % TWO_PI


def _angle_diff(a: float, b: float) -> float:
    d = abs(_wrap_phi(a) - _wrap_phi(b))
    return min(d, TWO_PI - d)


def _phi_key(phi: float, decimals: int = PHI_KEY_DECIMALS) -> float:
    """
    Stable phi identity key.

    Important:
    - Uses 12 decimals, not 6.
    - Prevents fine phi perturbation runs from being silently merged.
    """
    return round(_wrap_phi(phi), decimals)


def _extract_rows(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if path.suffix.lower() == ".jsonl":
        rows: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    data = json.loads(text)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("rows", "observations", "results", "report", "symbols"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]

    return []


def _extract_harmonics(obs: Dict[str, Any], meta: Dict[str, Any]) -> List[int]:
    harm = (
        obs.get("harmonics_hint")
        if "harmonics_hint" in obs
        else obs.get("harmonics", meta.get("harmonics"))
    )

    if isinstance(harm, list):
        out: List[int] = []
        for x in harm:
            try:
                out.append(int(x))
            except Exception:
                pass
        return out

    if harm is None:
        return []

    if isinstance(harm, str):
        s = harm.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    out: List[int] = []
                    for x in arr:
                        try:
                            out.append(int(x))
                        except Exception:
                            pass
                    return out
            except Exception:
                pass
        parts = [p.strip() for p in s.split(",") if p.strip()]
        out: List[int] = []
        for p in parts:
            try:
                out.append(int(float(p)))
            except Exception:
                pass
        return out

    try:
        return [int(harm)]
    except Exception:
        return []


def _row_to_obs(row: Dict[str, Any]) -> Dict[str, Any]:
    obs = row.get("observation", row)
    if not isinstance(obs, dict):
        obs = {}
    meta = obs.get("metadata", {})
    if not isinstance(meta, dict):
        meta = {}

    phi_raw = (
        obs.get("phi_hint")
        if "phi_hint" in obs
        else obs.get("phi", meta.get("phi", row.get("phi")))
    )
    phi = _wrap_phi(_safe_float(phi_raw, 0.0))

    harmonics = _extract_harmonics(obs, meta)

    pickup = _safe_float(
        obs.get(
            "pickup_mean",
            obs.get("pickup", row.get("pickup_mean", row.get("pickup", 0.0))),
        ),
        0.0,
    )
    stability = _safe_float(
        obs.get(
            "stability_mean",
            obs.get("stability", row.get("stability_mean", row.get("stability", 0.0))),
        ),
        0.0,
    )
    drift = _safe_float(
        obs.get("drift", row.get("drift", 0.0)),
        0.0,
    )
    voltage = _safe_float(
        obs.get("voltage_mean", row.get("voltage_mean", 0.0)),
        0.0,
    )
    locked = bool(obs.get("locked", row.get("locked", False)))

    source_name = (
        row.get("source_name")
        or obs.get("source_name")
        or row.get("label")
        or row.get("name")
        or meta.get("name")
        or ""
    )

    return {
        "source_name": source_name,
        "phi": phi,
        "phi_key": _phi_key(phi),
        "pickup_mean": pickup,
        "stability_mean": stability,
        "drift": drift,
        "voltage_mean": voltage,
        "locked": locked,
        "harmonics": harmonics,
        "harmonics_key": ",".join(str(h) for h in harmonics),
        "predicted_symbol_id": row.get("predicted_symbol_id", ""),
        "predicted_name": row.get("predicted_name", ""),
        "predicted_semantic_state": row.get("predicted_semantic_state", ""),
        "confidence": _safe_float(row.get("confidence"), 0.0),
        "margin": _safe_float(row.get("margin"), 0.0),
        "raw_row": row,
    }


def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mu = _mean(vals)
    return math.sqrt(sum((x - mu) ** 2 for x in vals) / len(vals))


def _best_null_center(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    best = min(rows, key=lambda r: (r["pickup_mean"], -r["stability_mean"], r["drift"]))
    return {
        "phi": best["phi"],
        "phi_key": best["phi_key"],
        "pickup_mean": best["pickup_mean"],
        "stability_mean": best["stability_mean"],
        "drift": best["drift"],
        "source_name": best["source_name"],
        "predicted_symbol_id": best["predicted_symbol_id"],
        "predicted_semantic_state": best["predicted_semantic_state"],
        "harmonics": best["harmonics"],
        "harmonics_key": best["harmonics_key"],
    }


def _corridor_rows(
    rows: List[Dict[str, Any]],
    center_phi: float,
    threshold: float,
    max_angle_distance: float = 1.0,
) -> List[Dict[str, Any]]:
    return [
        r
        for r in rows
        if r["pickup_mean"] <= threshold and _angle_diff(r["phi"], center_phi) <= max_angle_distance
    ]


def _estimate_width(
    rows: List[Dict[str, Any]],
    center_phi: float,
    threshold: float,
) -> Tuple[float, float, float]:
    inside = sorted(
        [r for r in rows if r["pickup_mean"] <= threshold],
        key=lambda r: r["phi"],
    )
    if not inside:
        return center_phi, center_phi, 0.0

    phis = [r["phi"] for r in inside]
    left_edge = min(phis)
    right_edge = max(phis)
    width = max(0.0, right_edge - left_edge)
    return left_edge, right_edge, width


def _symmetry_score(
    rows: List[Dict[str, Any]],
    center_phi: float,
) -> Dict[str, Any]:
    """
    Mirror-match rows around center_phi using precise phi keys and, where possible,
    same harmonic family.
    """
    by_key: Dict[Tuple[float, str], List[Dict[str, Any]]] = {}
    for r in rows:
        key = (r["phi_key"], r["harmonics_key"])
        by_key.setdefault(key, []).append(r)

    generic_by_phi: Dict[float, List[Dict[str, Any]]] = {}
    for r in rows:
        generic_by_phi.setdefault(r["phi_key"], []).append(r)

    used: set[Tuple[float, str, str]] = set()
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

    for r in rows:
        rid = (r["phi_key"], r["source_name"], r["harmonics_key"])
        if rid in used:
            continue

        mirror_phi = _wrap_phi(center_phi + (center_phi - r["phi"]))
        mirror_key = _phi_key(mirror_phi)

        candidates = by_key.get((mirror_key, r["harmonics_key"]), [])
        match = None

        for c in candidates:
            cid = (c["phi_key"], c["source_name"], c["harmonics_key"])
            if cid != rid and cid not in used:
                match = c
                break

        if match is None:
            for c in generic_by_phi.get(mirror_key, []):
                cid = (c["phi_key"], c["source_name"], c["harmonics_key"])
                if cid != rid and cid not in used:
                    match = c
                    break

        if match is None:
            continue

        cid = (match["phi_key"], match["source_name"], match["harmonics_key"])
        used.add(rid)
        used.add(cid)
        pairs.append((r, match))

    if not pairs:
        return {
            "num_pairs": 0,
            "pickup_mean_abs_diff": 0.0,
            "stability_mean_abs_diff": 0.0,
            "drift_mean_abs_diff": 0.0,
            "mean_pair_phi_error": 0.0,
            "phi_identity_decimals": PHI_KEY_DECIMALS,
        }

    pickup_diffs = [abs(a["pickup_mean"] - b["pickup_mean"]) for a, b in pairs]
    stability_diffs = [abs(a["stability_mean"] - b["stability_mean"]) for a, b in pairs]
    drift_diffs = [abs(a["drift"] - b["drift"]) for a, b in pairs]
    phi_errors = [
        abs(_angle_diff(a["phi"], center_phi) - _angle_diff(b["phi"], center_phi))
        for a, b in pairs
    ]

    return {
        "num_pairs": len(pairs),
        "pickup_mean_abs_diff": _mean(pickup_diffs),
        "stability_mean_abs_diff": _mean(stability_diffs),
        "drift_mean_abs_diff": _mean(drift_diffs),
        "mean_pair_phi_error": _mean(phi_errors),
        "phi_identity_decimals": PHI_KEY_DECIMALS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse π-corridor from Symatics sweep logs")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to decoder report JSON/JSONL or raw sweep JSONL",
    )
    parser.add_argument(
        "--phi-min",
        type=float,
        default=2.8,
        help="Lower phi bound to inspect",
    )
    parser.add_argument(
        "--phi-max",
        type=float,
        default=3.45,
        help="Upper phi bound to inspect",
    )
    parser.add_argument(
        "--threshold-mode",
        choices=["midpoint", "percent"],
        default="midpoint",
    )
    parser.add_argument(
        "--percent",
        type=float,
        default=0.25,
        help="For percent mode: corridor threshold = min + percent*(max-min)",
    )
    parser.add_argument(
        "--write-json",
        default="",
        help="Optional output JSON summary path",
    )
    args = parser.parse_args()

    path = Path(args.input)
    rows_raw = _extract_rows(path)
    rows = [_row_to_obs(r) for r in rows_raw]

    rows = [r for r in rows if args.phi_min <= r["phi"] <= args.phi_max]
    if not rows:
        raise SystemExit("No rows found in requested phi range.")

    rows = sorted(rows, key=lambda r: (r["phi"], r["harmonics_key"], r["source_name"]))

    pickups = [r["pickup_mean"] for r in rows]
    pickup_min = min(pickups)
    pickup_max = max(pickups)

    null_center = _best_null_center(rows)
    center_phi = null_center["phi"]

    if args.threshold_mode == "midpoint":
        threshold = pickup_min + 0.5 * (pickup_max - pickup_min)
    else:
        threshold = pickup_min + max(0.0, min(1.0, args.percent)) * (pickup_max - pickup_min)

    corridor = _corridor_rows(rows, center_phi, threshold)
    left_edge, right_edge, width = _estimate_width(rows, center_phi, threshold)
    symmetry = _symmetry_score(rows, center_phi)

    summary = {
        "input": str(path),
        "phi_window": [args.phi_min, args.phi_max],
        "num_rows": len(rows),
        "phi_identity_decimals": PHI_KEY_DECIMALS,
        "pickup_min": pickup_min,
        "pickup_max": pickup_max,
        "pickup_mean": _mean(pickups),
        "pickup_std": _std(pickups),
        "null_center": null_center,
        "distance_to_pi": abs(center_phi - PI),
        "threshold_mode": args.threshold_mode,
        "threshold_value": threshold,
        "corridor_size": len(corridor),
        "corridor_left_edge": left_edge,
        "corridor_right_edge": right_edge,
        "corridor_width": width,
        "symmetry": symmetry,
        "top_low_pickup_rows": [
            {
                "source_name": r["source_name"],
                "phi": r["phi"],
                "phi_key": r["phi_key"],
                "pickup_mean": r["pickup_mean"],
                "stability_mean": r["stability_mean"],
                "drift": r["drift"],
                "harmonics": r["harmonics"],
                "harmonics_key": r["harmonics_key"],
                "predicted_symbol_id": r["predicted_symbol_id"],
                "predicted_semantic_state": r["predicted_semantic_state"],
            }
            for r in sorted(
                rows,
                key=lambda r: (r["pickup_mean"], -r["stability_mean"], r["drift"]),
            )[:15]
        ],
    }

    print("\n=== PI CORRIDOR ANALYSIS ===")
    print(f"Input rows           : {summary['num_rows']}")
    print(f"Phi window           : [{args.phi_min:.12f}, {args.phi_max:.12f}]")
    print(f"Phi key decimals     : {PHI_KEY_DECIMALS}")
    print(f"Pickup range         : {pickup_min:.6f} .. {pickup_max:.6f}")
    print(f"Pickup mean ± std    : {_mean(pickups):.6f} ± {_std(pickups):.6f}")
    print()
    print("Null center candidate")
    print(f"  phi                : {null_center['phi']:.12f}")
    print(f"  phi_key            : {null_center['phi_key']:.12f}")
    print(f"  |phi-pi|           : {summary['distance_to_pi']:.12f}")
    print(f"  pickup_mean        : {null_center['pickup_mean']:.6f}")
    print(f"  stability_mean     : {null_center['stability_mean']:.6f}")
    print(f"  drift              : {null_center['drift']:.6f}")
    print(f"  harmonics          : {null_center['harmonics']}")
    print(f"  source             : {null_center['source_name']}")
    print(f"  predicted_symbol   : {null_center['predicted_symbol_id']}")
    print()
    print("Corridor")
    print(f"  threshold          : {threshold:.6f}")
    print(f"  rows under thresh  : {len(corridor)}")
    print(f"  left edge          : {left_edge:.12f}")
    print(f"  right edge         : {right_edge:.12f}")
    print(f"  width              : {width:.12f}")
    print()
    print("Symmetry around null")
    print(f"  pairs              : {symmetry['num_pairs']}")
    print(f"  mean |Δpickup|     : {symmetry['pickup_mean_abs_diff']:.6f}")
    print(f"  mean |Δstability|  : {symmetry['stability_mean_abs_diff']:.6f}")
    print(f"  mean |Δdrift|      : {symmetry['drift_mean_abs_diff']:.6f}")
    print(f"  mean |Δphi err|    : {symmetry['mean_pair_phi_error']:.12f}")
    print()
    print("Top low-pickup rows")
    for r in summary["top_low_pickup_rows"][:10]:
        print(
            f"  {r['source_name']} | phi={r['phi']:.12f} | "
            f"pickup={r['pickup_mean']:.6f} | stability={r['stability_mean']:.6f} | "
            f"drift={r['drift']:.6f} | harm={r['harmonics']} | pred={r['predicted_symbol_id']}"
        )

    if args.write_json:
        out = Path(args.write_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print()
        print(f"Wrote summary JSON: {out}")


if __name__ == "__main__":
    main()