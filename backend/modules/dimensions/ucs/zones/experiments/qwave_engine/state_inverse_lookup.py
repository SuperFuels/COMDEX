from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _float_or_none(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    return v


def _sort_key(r: dict[str, Any], destructive_first: bool) -> tuple[float, float, float]:
    pickup_norm = float(r.get("pickup_norm", 0.0))
    coherence = float(r.get("coherence", 0.0))
    stability = _float_or_none(r.get("stability")) or 0.0

    if destructive_first:
        return (pickup_norm, -coherence, -stability)
    return (-pickup_norm, -coherence, -stability)


def run(args: argparse.Namespace) -> None:
    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = data["rows"]

    matches: list[dict[str, Any]] = []

    for r in rows:
        ok = True

        if args.s_state and r.get("s_state") != args.s_state:
            ok = False
        if args.r_state and r.get("r_state") != args.r_state:
            ok = False
        if args.regime and r.get("observed_regime") != args.regime:
            ok = False

        if args.harmonic is not None and r.get("harmonic") != args.harmonic:
            ok = False

        alpha = _float_or_none(r.get("alpha"))
        if args.alpha_min is not None:
            if alpha is None or alpha < args.alpha_min:
                ok = False
        if args.alpha_max is not None:
            if alpha is None or alpha > args.alpha_max:
                ok = False

        nu = _float_or_none(r.get("nu"))
        if args.nu_min is not None:
            if nu is None or nu < args.nu_min:
                ok = False
        if args.nu_max is not None:
            if nu is None or nu > args.nu_max:
                ok = False

        drift = _float_or_none(r.get("drift"))
        if args.max_drift is not None:
            if drift is None or drift > args.max_drift:
                ok = False

        coherence = _float_or_none(r.get("coherence"))
        if args.min_coherence is not None:
            if coherence is None or coherence < args.min_coherence:
                ok = False

        pickup_norm = _float_or_none(r.get("pickup_norm"))
        if args.pickup_norm_min is not None:
            if pickup_norm is None or pickup_norm < args.pickup_norm_min:
                ok = False
        if args.pickup_norm_max is not None:
            if pickup_norm is None or pickup_norm > args.pickup_norm_max:
                ok = False

        if ok:
            matches.append(r)

    destructive_first = args.s_state == "S4_destructive" or (
        args.regime is not None and str(args.regime).startswith("A4_null")
    )
    matches.sort(key=lambda r: _sort_key(r, destructive_first=destructive_first))

    print("\n=== STATE INVERSE LOOKUP ===\n")
    print(f"input            : {args.input}")
    print(f"s_state          : {args.s_state}")
    print(f"r_state          : {args.r_state}")
    print(f"regime           : {args.regime}")
    print(f"harmonic         : {args.harmonic}")
    print(f"alpha_min/max    : {args.alpha_min} / {args.alpha_max}")
    print(f"nu_min/max       : {args.nu_min} / {args.nu_max}")
    print(f"min_coherence    : {args.min_coherence}")
    print(f"max_drift        : {args.max_drift}")
    print(f"pickup_norm min/max : {args.pickup_norm_min} / {args.pickup_norm_max}")
    print(f"matches          : {len(matches)}\n")

    for r in matches[: args.top_k]:
        alpha = _float_or_none(r.get("alpha"))
        nu = _float_or_none(r.get("nu"))
        drift = _float_or_none(r.get("drift"))
        stability = _float_or_none(r.get("stability"))

        alpha_txt = f"{alpha:.3f}" if alpha is not None else "nan"
        nu_txt = f"{nu:.3f}" if nu is not None else "nan"
        drift_txt = f"{drift:.6f}" if drift is not None else "nan"
        stab_txt = f"{stability:.6f}" if stability is not None else "nan"

        print(
            f"phi={float(r['phi']):.6f} | "
            f"h={r.get('harmonic', 'na')} | "
            f"alpha={alpha_txt} | "
            f"nu={nu_txt} | "
            f"pickup={float(r['pickup']):.6f} | "
            f"pickup_norm={float(r['pickup_norm']):.6f} | "
            f"coh={float(r['coherence']):.6f} | "
            f"drift={drift_txt} | "
            f"stability={stab_txt} | "
            f"{r['combined_state']}"
        )

    if args.json_out:
        out = {
            "query": {
                "s_state": args.s_state,
                "r_state": args.r_state,
                "regime": args.regime,
                "harmonic": args.harmonic,
                "alpha_min": args.alpha_min,
                "alpha_max": args.alpha_max,
                "nu_min": args.nu_min,
                "nu_max": args.nu_max,
                "min_coherence": args.min_coherence,
                "max_drift": args.max_drift,
                "pickup_norm_min": args.pickup_norm_min,
                "pickup_norm_max": args.pickup_norm_max,
                "top_k": args.top_k,
            },
            "match_count": len(matches),
            "matches": matches[: args.top_k],
        }
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nWrote JSON: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Find best parameters for a desired Symatics state.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--s-state", default=None)
    ap.add_argument("--r-state", default=None)
    ap.add_argument("--regime", default=None)

    ap.add_argument("--harmonic", type=int, default=None)
    ap.add_argument("--alpha-min", type=float, default=None)
    ap.add_argument("--alpha-max", type=float, default=None)
    ap.add_argument("--nu-min", type=float, default=None)
    ap.add_argument("--nu-max", type=float, default=None)

    ap.add_argument("--min-coherence", type=float, default=None)
    ap.add_argument("--max-drift", type=float, default=None)
    ap.add_argument("--pickup-norm-min", type=float, default=None)
    ap.add_argument("--pickup-norm-max", type=float, default=None)

    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument(
        "--json-out",
        default="backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/state_inverse_lookup_latest.json",
    )
    run(ap.parse_args())