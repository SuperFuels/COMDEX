from __future__ import annotations

import argparse
import json
import math
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.sensor_bridge import (
    SensorBridge,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)

OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TWO_PI = 2.0 * math.pi


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mu = _mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))


def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _phase_distance(a: float, b: float) -> float:
    a = _wrap_phase(a)
    b = _wrap_phase(b)
    d = abs(a - b)
    return min(d, TWO_PI - d)


def _circular_mean(phases: List[float]) -> float:
    if not phases:
        return 0.0
    s = sum(math.sin(_wrap_phase(p)) for p in phases)
    c = sum(math.cos(_wrap_phase(p)) for p in phases)
    if abs(s) < 1e-12 and abs(c) < 1e-12:
        return _wrap_phase(phases[0])
    return _wrap_phase(math.atan2(s, c))


def _circular_std(phases: List[float]) -> float:
    if len(phases) < 2:
        return 0.0
    mu = _circular_mean(phases)
    return math.sqrt(sum(_phase_distance(p, mu) ** 2 for p in phases) / len(phases))


def _profile_to_context(profile: Any) -> Dict[str, Any]:
    if profile is None:
        return {}

    metadata = getattr(profile, "metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "label": getattr(profile, "label", ""),
        "phi": float(getattr(profile, "phi", 0.0)),
        "amplitude": float(getattr(profile, "amplitude", 1.0)),
        "frequency": float(getattr(profile, "frequency", 1.0)),
        "harmonics": list(getattr(profile, "harmonics", [1])),
        "duty_cycle": float(getattr(profile, "duty_cycle", 0.5)),
        "envelope": str(getattr(profile, "envelope", "steady")),
        "interference_factor": float(getattr(profile, "interference_factor", 0.0)),
        "metadata": dict(metadata),
    }


def run_capture(
    engine: Any,
    sensors: SensorBridge,
    *,
    phi: float,
    harmonics: List[int],
    amplitude: float,
    frequency: float,
    ticks: int,
    tick_sleep: float,
    label: str,
) -> Dict[str, Any]:
    expr = engine.compiler.phase_probe(
        phi=phi,
        frequency=frequency,
        amplitude=amplitude,
        harmonics=harmonics,
    )

    engine.reset_runtime(clear_feedback=True)
    engine.load_expression(expr)

    phase_vals: List[float] = []
    voltage_vals: List[float] = []
    stability_vals: List[float] = []
    pickup_vals: List[float] = []
    aux1_vals: List[float] = []
    aux2_vals: List[float] = []
    mx_vals: List[float] = []
    my_vals: List[float] = []
    mz_vals: List[float] = []

    locked = False

    for _ in range(ticks):
        feedback = engine.stabilize_step()
        current_profile = engine.current_profile

        sensors.update_emission_context(_profile_to_context(current_profile))
        snapshot = sensors.read_all()
        snap = snapshot.to_dict()

        phase_vals.append(_wrap_phase(_safe_float(feedback.measured_phase, 0.0)))
        voltage_vals.append(_safe_float(feedback.measured_voltage, 0.0))
        stability_vals.append(_safe_float(feedback.stability_score, 0.0))

        pickup_vals.append(_safe_float(snap.get("pickup_voltage"), 0.0))
        aux1_vals.append(_safe_float(snap.get("aux_adc_1"), 0.0))
        aux2_vals.append(_safe_float(snap.get("aux_adc_2"), 0.0))
        mx_vals.append(_safe_float(snap.get("magnetometer_x"), 0.0))
        my_vals.append(_safe_float(snap.get("magnetometer_y"), 0.0))
        mz_vals.append(_safe_float(snap.get("magnetometer_z"), 0.0))

        is_locked_fn = getattr(engine, "is_locked", None)
        if callable(is_locked_fn):
            locked = locked or bool(is_locked_fn())

        if tick_sleep > 0:
            time.sleep(tick_sleep)

    return {
        "source_name": label,
        "source_kind": "parameter_sweep",
        "semantic_hint": "candidate",
        "phi_hint": _wrap_phase(phi),
        "harmonics_hint": list(harmonics),
        "stability_mean": _mean(stability_vals),
        "drift": _circular_std(phase_vals),
        "voltage_mean": _mean(voltage_vals),
        "pickup_mean": _mean(pickup_vals),
        "pickup_std": _std(pickup_vals),
        "aux_adc_1_mean": _mean(aux1_vals),
        "aux_adc_2_mean": _mean(aux2_vals),
        "magnetometer_x_mean": _mean(mx_vals),
        "magnetometer_y_mean": _mean(my_vals),
        "magnetometer_z_mean": _mean(mz_vals),
        "ticks": ticks,
        "locked": locked,
        "metadata": {
            "sweep_label": label,
            "phi": _wrap_phase(phi),
            "harmonics": list(harmonics),
            "amplitude": amplitude,
            "frequency": frequency,
        },
    }


def parse_harmonic_sets(text: str) -> List[List[int]]:
    """
    Example input:
        "1|1,2|1,3|2,3|1,2,3"
    """
    out: List[List[int]] = []
    for block in text.split("|"):
        block = block.strip()
        if not block:
            continue
        vals = []
        for tok in block.split(","):
            tok = tok.strip()
            if not tok:
                continue
            vals.append(max(1, int(tok)))
        if vals:
            out.append(vals)
    return out or [[1], [1, 2], [1, 3]]


def parse_phi_list(text: str) -> List[float]:
    out: List[float] = []
    for tok in text.split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(float(tok))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--safe-mode", action="store_true")
    ap.add_argument("--ticks", type=int, default=40)
    ap.add_argument("--tick-sleep", type=float, default=0.0)
    ap.add_argument("--frequency", type=float, default=1.0)
    ap.add_argument("--amplitude", type=float, default=1.0)
    ap.add_argument(
        "--phis",
        default="0.0,0.78539816339,1.57079632679,2.35619449019,3.14159265359,3.92699081699,4.71238898038,5.49778714378",
        help="Comma-separated phase list in radians",
    )
    ap.add_argument(
        "--harmonic-sets",
        default="1|1,2|1,3|2,3|1,2,3",
        help='Pipe-separated harmonic sets, e.g. "1|1,2|1,3|2,3|1,2,3"',
    )
    ap.add_argument("--limit", type=int, default=0, help="Optional max combinations")
    ap.add_argument(
        "--out",
        default="",
        help="Optional explicit output jsonl path",
    )
    args = ap.parse_args()

    phis = parse_phi_list(args.phis)
    harmonic_sets = parse_harmonic_sets(args.harmonic_sets)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out_path = Path(args.out) if args.out else OUTPUT_DIR / f"symatics_capture_sweep_{stamp}.jsonl"

    engine = build_hello_world_engine(safe_mode=args.safe_mode)
    sensors = SensorBridge(safe_mode=args.safe_mode)

    combos = list(product(phis, harmonic_sets))
    if args.limit and args.limit > 0:
        combos = combos[: args.limit]

    try:
        with out_path.open("w", encoding="utf-8") as f:
            for idx, (phi, harmonics) in enumerate(combos, start=1):
                label = f"cand_{idx:03d}_phi_{phi:.6f}_harm_{'-'.join(map(str, harmonics))}"
                row = run_capture(
                    engine,
                    sensors,
                    phi=phi,
                    harmonics=harmonics,
                    amplitude=args.amplitude,
                    frequency=args.frequency,
                    ticks=args.ticks,
                    tick_sleep=args.tick_sleep,
                    label=label,
                )
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(
                    f"[{idx}/{len(combos)}] {label} | "
                    f"pickup={row['pickup_mean']:.6f} | "
                    f"stability={row['stability_mean']:.6f} | "
                    f"drift={row['drift']:.6f} | "
                    f"locked={row['locked']}"
                )
    finally:
        shutdown = getattr(engine, "shutdown", None)
        if callable(shutdown):
            shutdown()

    print()
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()