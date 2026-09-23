from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.sensor_bridge import (
    SensorBridge,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)

OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

TWO_PI = 2.0 * math.pi


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def _minmax(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"min": 0.0, "max": 0.0}
    return {"min": min(values), "max": max(values)}


def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _phase_distance(a: float, b: float) -> float:
    a = _wrap_phase(a)
    b = _wrap_phase(b)
    d = abs(a - b)
    return min(d, TWO_PI - d)


def _circular_phase_mean(phases: List[float]) -> float:
    if not phases:
        return 0.0
    s = sum(math.sin(_wrap_phase(p)) for p in phases)
    c = sum(math.cos(_wrap_phase(p)) for p in phases)
    if abs(s) < 1e-12 and abs(c) < 1e-12:
        return _wrap_phase(phases[0])
    return _wrap_phase(math.atan2(s, c))


def _circular_phase_std(phases: List[float]) -> float:
    if len(phases) < 2:
        return 0.0
    mu = _circular_phase_mean(phases)
    deltas = [_phase_distance(p, mu) for p in phases]
    var = sum(d * d for d in deltas) / len(deltas)
    return math.sqrt(var)


def _parse_harmonic_token(token: str) -> List[int]:
    token = str(token).strip()
    if not token:
        return [1]
    out: List[int] = []
    for part in token.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(max(1, int(part)))
    return out or [1]


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


def _utc_stamp() -> str:
    # microseconds avoid same-second overwrite during replicate loops
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _parse_float_list(values: Iterable[float] | None, fallback: List[float]) -> List[float]:
    out: List[float] = []
    if values is not None:
        for v in values:
            out.append(float(v))
    return out or list(fallback)


def _capture_step(
    *,
    engine: Any,
    sensors: SensorBridge,
    quiet_sim: bool,
) -> Dict[str, Any]:
    if quiet_sim:
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            feedback = engine.stabilize_step()
            current_profile = engine.current_profile
            sensors.update_emission_context(_profile_to_context(current_profile))
            snap = sensors.read_all().to_dict()
    else:
        feedback = engine.stabilize_step()
        current_profile = engine.current_profile
        sensors.update_emission_context(_profile_to_context(current_profile))
        snap = sensors.read_all().to_dict()

    return {
        "feedback": feedback,
        "profile": current_profile,
        "snap": snap,
    }


def _append_capture(
    *,
    feedback: Any,
    current_profile: Any,
    snap: Dict[str, Any],
    phi_fallback: float,
    frequency_fallback: float,
    amplitude_fallback: float,
    phase_vals: List[float],
    target_phase_vals: List[float],
    voltage_vals: List[float],
    stability_vals: List[float],
    pickup_vals: List[float],
    aux1_vals: List[float],
    aux2_vals: List[float],
    mx_vals: List[float],
    my_vals: List[float],
    mz_vals: List[float],
    freq_vals: List[float],
    amp_vals: List[float],
    duty_vals: List[float],
    factor_vals: List[float],
    pickup_trace: List[float],
    stability_trace: List[float],
    phase_trace: List[float],
    voltage_trace: List[float],
    target_phase_trace: List[float],
    trace_max_points: int,
    store_traces: bool,
) -> None:
    measured_phase = _wrap_phase(
        _safe_float(getattr(feedback, "measured_phase", 0.0), 0.0)
    )
    target_phase = _wrap_phase(
        _safe_float(getattr(current_profile, "phi", phi_fallback), float(phi_fallback))
    )
    measured_voltage = _safe_float(
        getattr(feedback, "measured_voltage", 0.0), 0.0
    )
    stability_score = _safe_float(
        getattr(feedback, "stability_score", 0.0), 0.0
    )
    pickup_voltage = _safe_float(snap.get("pickup_voltage"), 0.0)
    aux1 = _safe_float(snap.get("aux_adc_1"), 0.0)
    aux2 = _safe_float(snap.get("aux_adc_2"), 0.0)
    mx = _safe_float(snap.get("magnetometer_x"), 0.0)
    my = _safe_float(snap.get("magnetometer_y"), 0.0)
    mz = _safe_float(snap.get("magnetometer_z"), 0.0)
    freq = _safe_float(
        getattr(current_profile, "frequency", frequency_fallback), 0.0
    )
    amp = _safe_float(
        getattr(current_profile, "amplitude", amplitude_fallback), 0.0
    )
    duty = _safe_float(
        getattr(current_profile, "duty_cycle", 0.5), 0.0
    )
    factor = _safe_float(
        getattr(current_profile, "interference_factor", 0.0), 0.0
    )

    phase_vals.append(measured_phase)
    target_phase_vals.append(target_phase)
    voltage_vals.append(measured_voltage)
    stability_vals.append(stability_score)
    pickup_vals.append(pickup_voltage)
    aux1_vals.append(aux1)
    aux2_vals.append(aux2)
    mx_vals.append(mx)
    my_vals.append(my)
    mz_vals.append(mz)
    freq_vals.append(freq)
    amp_vals.append(amp)
    duty_vals.append(duty)
    factor_vals.append(factor)

    if store_traces and len(pickup_trace) < trace_max_points:
        pickup_trace.append(pickup_voltage)
        stability_trace.append(stability_score)
        phase_trace.append(measured_phase)
        voltage_trace.append(measured_voltage)
        target_phase_trace.append(target_phase)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual Symatics capture sweep")

    parser.add_argument("--phis", nargs="+", type=float, required=True)
    parser.add_argument("--harmonics", nargs="+", required=True)

    parser.add_argument(
        "--ticks",
        type=int,
        default=40,
        help="Capture ticks after warmup.",
    )
    parser.add_argument(
        "--warmup-ticks",
        type=int,
        default=0,
        help="Warmup/settle ticks before capture begins.",
    )
    parser.add_argument("--frequency", type=float, default=100.0)
    parser.add_argument("--amplitude", type=float, default=1.0)

    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--nu", type=float, default=None)

    parser.add_argument("--alphas", nargs="+", type=float, default=None)
    parser.add_argument("--nus", nargs="+", type=float, default=None)

    parser.add_argument("--safe-mode", action="store_true")
    parser.add_argument("--quiet-sim", action="store_true")
    parser.add_argument("--store-series", action="store_true")
    parser.add_argument("--store-traces", action="store_true")
    parser.add_argument("--trace-max-points", type=int, default=512)

    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"symatics_capture_sweep_{_utc_stamp()}.jsonl"

    harmonic_sets = [_parse_harmonic_token(x) for x in args.harmonics]

    alpha_values = _parse_float_list(
        args.alphas,
        [args.alpha] if args.alpha is not None else [0.10],
    )
    nu_values = _parse_float_list(
        args.nus,
        [args.nu] if args.nu is not None else [0.08],
    )

    engine = build_hello_world_engine(safe_mode=args.safe_mode)
    sensors = SensorBridge(safe_mode=args.safe_mode)

    rows: List[Dict[str, Any]] = []
    idx = 0
    total = len(args.phis) * len(harmonic_sets) * len(alpha_values) * len(nu_values)

    try:
        for phi in args.phis:
            for harmonics in harmonic_sets:
                for alpha in alpha_values:
                    for nu in nu_values:
                        idx += 1
                        label = (
                            f"cand_{idx:03d}"
                            f"_phi_{phi:.6f}"
                            f"_harm_{'-'.join(str(h) for h in harmonics)}"
                            f"_a_{alpha:.3f}"
                            f"_n_{nu:.3f}"
                        )

                        expr = engine.compiler.phase_probe(
                            phi=float(phi),
                            frequency=float(args.frequency),
                            amplitude=float(args.amplitude),
                            harmonics=list(harmonics),
                        )

                        engine.reset_runtime(clear_feedback=True)
                        engine.load_expression(expr)

                        runtime = getattr(engine, "runtime", None)
                        if runtime is not None:
                            if hasattr(runtime, "alpha"):
                                runtime.alpha = float(alpha)
                            if hasattr(runtime, "nu"):
                                runtime.nu = float(nu)

                        # Warmup first; do not record traces or metrics.
                        for _ in range(max(0, int(args.warmup_ticks))):
                            _capture_step(
                                engine=engine,
                                sensors=sensors,
                                quiet_sim=args.quiet_sim,
                            )

                        phase_vals: List[float] = []
                        target_phase_vals: List[float] = []
                        voltage_vals: List[float] = []
                        stability_vals: List[float] = []
                        pickup_vals: List[float] = []
                        aux1_vals: List[float] = []
                        aux2_vals: List[float] = []
                        mx_vals: List[float] = []
                        my_vals: List[float] = []
                        mz_vals: List[float] = []
                        freq_vals: List[float] = []
                        amp_vals: List[float] = []
                        duty_vals: List[float] = []
                        factor_vals: List[float] = []

                        pickup_trace: List[float] = []
                        stability_trace: List[float] = []
                        phase_trace: List[float] = []
                        voltage_trace: List[float] = []
                        target_phase_trace: List[float] = []

                        locked = False

                        for _ in range(args.ticks):
                            captured = _capture_step(
                                engine=engine,
                                sensors=sensors,
                                quiet_sim=args.quiet_sim,
                            )
                            feedback = captured["feedback"]
                            current_profile = captured["profile"]
                            snap = captured["snap"]

                            _append_capture(
                                feedback=feedback,
                                current_profile=current_profile,
                                snap=snap,
                                phi_fallback=float(phi),
                                frequency_fallback=float(args.frequency),
                                amplitude_fallback=float(args.amplitude),
                                phase_vals=phase_vals,
                                target_phase_vals=target_phase_vals,
                                voltage_vals=voltage_vals,
                                stability_vals=stability_vals,
                                pickup_vals=pickup_vals,
                                aux1_vals=aux1_vals,
                                aux2_vals=aux2_vals,
                                mx_vals=mx_vals,
                                my_vals=my_vals,
                                mz_vals=mz_vals,
                                freq_vals=freq_vals,
                                amp_vals=amp_vals,
                                duty_vals=duty_vals,
                                factor_vals=factor_vals,
                                pickup_trace=pickup_trace,
                                stability_trace=stability_trace,
                                phase_trace=phase_trace,
                                voltage_trace=voltage_trace,
                                target_phase_trace=target_phase_trace,
                                trace_max_points=max(0, int(args.trace_max_points)),
                                store_traces=bool(args.store_traces),
                            )

                            is_locked_fn = getattr(engine, "is_locked", None)
                            if callable(is_locked_fn):
                                locked = locked or bool(is_locked_fn())

                        phase_err_vals = [
                            _phase_distance(a, b) for a, b in zip(phase_vals, target_phase_vals)
                        ]

                        pickup_mm = _minmax(pickup_vals)
                        stability_mm = _minmax(stability_vals)
                        voltage_mm = _minmax(voltage_vals)
                        freq_mm = _minmax(freq_vals)
                        amp_mm = _minmax(amp_vals)
                        duty_mm = _minmax(duty_vals)
                        factor_mm = _minmax(factor_vals)

                        row: Dict[str, Any] = {
                            "source_name": label,
                            "source_kind": "parameter_sweep",
                            "semantic_hint": "candidate",
                            "phi_hint": float(phi),
                            "harmonics_hint": list(harmonics),
                            "alpha_hint": float(alpha),
                            "nu_hint": float(nu),
                            "stability_mean": _mean(stability_vals),
                            "stability_std": _std(stability_vals),
                            "stability_min": stability_mm["min"],
                            "stability_max": stability_mm["max"],
                            "drift": _circular_phase_std(phase_vals),
                            "phase_mean": _circular_phase_mean(phase_vals),
                            "phase_target_mean": _circular_phase_mean(target_phase_vals),
                            "phase_error_mean": _mean(phase_err_vals),
                            "phase_error_std": _std(phase_err_vals),
                            "voltage_mean": _mean(voltage_vals),
                            "voltage_std": _std(voltage_vals),
                            "voltage_min": voltage_mm["min"],
                            "voltage_max": voltage_mm["max"],
                            "pickup_mean": _mean(pickup_vals),
                            "pickup_std": _std(pickup_vals),
                            "pickup_min": pickup_mm["min"],
                            "pickup_max": pickup_mm["max"],
                            "aux_adc_1_mean": _mean(aux1_vals),
                            "aux_adc_2_mean": _mean(aux2_vals),
                            "magnetometer_x_mean": _mean(mx_vals),
                            "magnetometer_y_mean": _mean(my_vals),
                            "magnetometer_z_mean": _mean(mz_vals),
                            "frequency_mean": _mean(freq_vals),
                            "frequency_std": _std(freq_vals),
                            "frequency_min": freq_mm["min"],
                            "frequency_max": freq_mm["max"],
                            "amplitude_mean": _mean(amp_vals),
                            "amplitude_std": _std(amp_vals),
                            "amplitude_min": amp_mm["min"],
                            "amplitude_max": amp_mm["max"],
                            "duty_cycle_mean": _mean(duty_vals),
                            "duty_cycle_std": _std(duty_vals),
                            "duty_cycle_min": duty_mm["min"],
                            "duty_cycle_max": duty_mm["max"],
                            "interference_factor_mean": _mean(factor_vals),
                            "interference_factor_std": _std(factor_vals),
                            "interference_factor_min": factor_mm["min"],
                            "interference_factor_max": factor_mm["max"],
                            "ticks": int(args.ticks),
                            "warmup_ticks": int(args.warmup_ticks),
                            "locked": bool(locked),
                            "pickup_trace": pickup_trace if args.store_traces else [],
                            "stability_trace": stability_trace if args.store_traces else [],
                            "phase_trace": phase_trace if args.store_traces else [],
                            "phase_target_trace": target_phase_trace if args.store_traces else [],
                            "voltage_trace": voltage_trace if args.store_traces else [],
                            "metadata": {
                                "sweep_label": label,
                                "phi": float(phi),
                                "harmonics": list(harmonics),
                                "amplitude": float(args.amplitude),
                                "frequency": float(args.frequency),
                                "alpha": float(alpha),
                                "nu": float(nu),
                                "store_traces": bool(args.store_traces),
                                "trace_max_points": int(args.trace_max_points),
                                "warmup_ticks": int(args.warmup_ticks),
                            },
                        }

                        if args.store_series:
                            row["series"] = {
                                "tick": list(range(args.ticks)),
                                "phase": phase_vals,
                                "phase_target": target_phase_vals,
                                "phase_error": phase_err_vals,
                                "voltage": voltage_vals,
                                "stability": stability_vals,
                                "pickup": pickup_vals,
                                "aux_adc_1": aux1_vals,
                                "aux_adc_2": aux2_vals,
                                "magnetometer_x": mx_vals,
                                "magnetometer_y": my_vals,
                                "magnetometer_z": mz_vals,
                                "frequency": freq_vals,
                                "amplitude": amp_vals,
                                "duty_cycle": duty_vals,
                                "interference_factor": factor_vals,
                            }

                        rows.append(row)

                        trace_note = f" | traces={len(pickup_trace)}" if args.store_traces else ""
                        print(
                            f"[{idx:03d}/{total:03d}] "
                            f"{label} | pickup={row['pickup_mean']:.6f} | "
                            f"stability={row['stability_mean']:.6f} | "
                            f"drift={row['drift']:.6f} | locked={row['locked']}"
                            f"{trace_note}"
                        )

    finally:
        shutdown = getattr(engine, "shutdown", None)
        if callable(shutdown):
            shutdown()

    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print()
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()