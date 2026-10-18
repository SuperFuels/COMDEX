from __future__ import annotations

"""
Symatics Phase Map
------------------
Scans symbolic phase/harmonic space, captures lock quality, and writes:

- CSV summary
- JSON summary

This is the next stage after single-state capture:
    phi/harmonics -> run engine -> evaluate lock quality -> rank stable regions

Outputs:
- backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_phase_map.json
- backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_phase_map.csv
"""

import argparse
import csv
import json
import math
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.sensor_bridge import SensorBridge
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)

OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Map stable Symatics symbolic regions")
    parser.add_argument("--safe-mode", action="store_true", help="Use simulated hardware")
    parser.add_argument("--steps", type=int, default=25, help="Number of phi points over [0, 2π]")
    parser.add_argument("--ticks", type=int, default=30, help="Ticks per state")
    parser.add_argument("--amplitude", type=float, default=1.0, help="Base amplitude")
    parser.add_argument("--frequency", type=float, default=1.0, help="Base symbolic frequency")
    parser.add_argument(
        "--harmonic-sets",
        nargs="+",
        default=["1", "1,2", "1,2,3"],
        help='Space-separated harmonic sets, e.g. "1" "1,2" "1,2,3"',
    )
    parser.add_argument(
        "--drift-threshold",
        type=float,
        default=0.05,
        help="Lock drift threshold",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="How many top regions to print",
    )
    return parser


def parse_harmonic_sets(values: Sequence[str]) -> List[List[int]]:
    out: List[List[int]] = []
    for value in values:
        hs = [max(1, int(x.strip())) for x in value.split(",") if x.strip()]
        if hs:
            out.append(hs)
    return out or [[1], [1, 2], [1, 2, 3]]


def semantic_state(phi: float) -> str:
    two_pi = 2.0 * math.pi
    phi = phi % two_pi
    eps = 1e-6

    if abs(phi - 0.0) < eps or abs(phi - two_pi) < eps:
        return "constructive"
    if abs(phi - math.pi) < eps:
        return "destructive"
    if abs(phi - (math.pi / 2.0)) < eps:
        return "beyond_boolean_positive"
    if abs(phi - (3.0 * math.pi / 2.0)) < eps:
        return "beyond_boolean_negative"
    return "intermediate"


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def pstdev(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / len(values))


def dataclass_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def rank_quality(
    locked: bool,
    stability_mean: float,
    drift_value: float,
    pickup_mean: float,
    pickup_std: float,
    aux_means: Sequence[float],
    mag_abs_mean: float,
) -> float:
    lock_bonus = 1.0 if locked else 0.0
    drift_score = max(0.0, 1.0 - (drift_value / 0.1))
    pickup_score = max(0.0, pickup_mean - pickup_std)
    aux_score = mean(aux_means)
    mag_score = mag_abs_mean

    return (
        (2.5 * stability_mean)
        + (1.5 * drift_score)
        + (1.5 * pickup_score)
        + (0.8 * aux_score)
        + (0.6 * mag_score)
        + lock_bonus
    )


def run_region(
    engine: Any,
    sensors: SensorBridge,
    phi: float,
    harmonics: List[int],
    amplitude: float,
    frequency: float,
    ticks: int,
    drift_threshold: float,
) -> Dict[str, Any]:
    compiler = engine.compiler

    expr = compiler.phase_probe(
        phi=phi,
        frequency=frequency,
        amplitude=amplitude,
        harmonics=harmonics,
    )

    engine.reset_runtime(clear_feedback=True)
    engine.load_expression(expr)

    stability_scores: List[float] = []
    voltages: List[float] = []
    pickup_values: List[float] = []
    aux1_values: List[float] = []
    aux2_values: List[float] = []
    magx_values: List[float] = []
    magy_values: List[float] = []
    magz_values: List[float] = []

    last_feedback = None

    for _ in range(ticks):
        feedback = engine.stabilize_step()
        last_feedback = feedback

        current_profile = engine.current_profile
        context = {
            "label": current_profile.label if current_profile else "unknown",
            "phi": float(current_profile.phi) if current_profile else float(phi),
            "amplitude": float(current_profile.amplitude) if current_profile else float(amplitude),
            "frequency": float(current_profile.frequency) if current_profile else float(frequency),
            "harmonics": list(current_profile.harmonics) if current_profile else list(harmonics),
            "duty_cycle": float(current_profile.duty_cycle) if current_profile else 0.5,
            "envelope": str(current_profile.envelope) if current_profile else "steady",
            "interference_factor": float(current_profile.interference_factor) if current_profile else 0.0,
            "metadata": dict(current_profile.metadata) if current_profile else {},
        }
        sensors.update_emission_context(context)
        snapshot = sensors.read_all().to_dict()

        stability_scores.append(float(feedback.stability_score))
        voltages.append(float(feedback.measured_voltage))

        pickup_values.append(float(snapshot.get("pickup_voltage", 0.0)))
        aux1_values.append(float(snapshot.get("aux_adc_1", 0.0)))
        aux2_values.append(float(snapshot.get("aux_adc_2", 0.0)))
        magx_values.append(float(snapshot.get("magnetometer_x", 0.0)))
        magy_values.append(float(snapshot.get("magnetometer_y", 0.0)))
        magz_values.append(float(snapshot.get("magnetometer_z", 0.0)))

        time.sleep(engine.tick_delay_s)

    drift_value = float(engine.stabilizer.drift())
    locked = bool(engine.stabilizer.is_locked(drift_threshold=drift_threshold))
    stability_mean = mean(stability_scores)
    voltage_mean = mean(voltages)
    pickup_mean = mean(pickup_values)
    pickup_std = pstdev(pickup_values)
    aux1_mean = mean(aux1_values)
    aux2_mean = mean(aux2_values)
    magx_mean = mean(magx_values)
    magy_mean = mean(magy_values)
    magz_mean = mean(magz_values)

    mag_abs_mean = mean([abs(magx_mean), abs(magy_mean), abs(magz_mean)])

    quality = rank_quality(
        locked=locked,
        stability_mean=stability_mean,
        drift_value=drift_value,
        pickup_mean=pickup_mean,
        pickup_std=pickup_std,
        aux_means=[aux1_mean, aux2_mean],
        mag_abs_mean=mag_abs_mean,
    )

    final_profile = engine.current_profile

    return {
        "phi": float(phi),
        "phi_deg": float(math.degrees(phi)),
        "semantic_state": semantic_state(phi),
        "harmonics": list(harmonics),
        "ticks": int(ticks),
        "locked": locked,
        "drift": drift_value,
        "stability_mean": stability_mean,
        "voltage_mean": voltage_mean,
        "pickup_mean": pickup_mean,
        "pickup_std": pickup_std,
        "aux_adc_1_mean": aux1_mean,
        "aux_adc_2_mean": aux2_mean,
        "magnetometer_x_mean": magx_mean,
        "magnetometer_y_mean": magy_mean,
        "magnetometer_z_mean": magz_mean,
        "quality": quality,
        "final_profile": dataclass_to_dict(final_profile),
        "last_feedback": dataclass_to_dict(last_feedback),
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "phi",
        "phi_deg",
        "semantic_state",
        "harmonics",
        "ticks",
        "locked",
        "drift",
        "stability_mean",
        "voltage_mean",
        "pickup_mean",
        "pickup_std",
        "aux_adc_1_mean",
        "aux_adc_2_mean",
        "magnetometer_x_mean",
        "magnetometer_y_mean",
        "magnetometer_z_mean",
        "quality",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{k: row[k] for k in fieldnames if k != "harmonics"},
                    "harmonics": ",".join(str(h) for h in row["harmonics"]),
                }
            )


def main() -> None:
    args = build_parser().parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    harmonic_sets = parse_harmonic_sets(args.harmonic_sets)

    engine = build_hello_world_engine(safe_mode=args.safe_mode)
    sensors = SensorBridge(safe_mode=args.safe_mode)

    if args.steps < 2:
        phases = [0.0]
    else:
        phases = [(2.0 * math.pi) * i / (args.steps - 1) for i in range(args.steps)]

    rows: List[Dict[str, Any]] = []

    for harmonics in harmonic_sets:
        for phi in phases:
            row = run_region(
                engine=engine,
                sensors=sensors,
                phi=phi,
                harmonics=harmonics,
                amplitude=args.amplitude,
                frequency=args.frequency,
                ticks=args.ticks,
                drift_threshold=args.drift_threshold,
            )
            rows.append(row)

    rows.sort(key=lambda r: r["quality"], reverse=True)

    json_path = OUTPUT_DIR / "symatics_phase_map.json"
    csv_path = OUTPUT_DIR / "symatics_phase_map.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": time.time(),
                "safe_mode": bool(args.safe_mode),
                "steps": int(args.steps),
                "ticks": int(args.ticks),
                "amplitude": float(args.amplitude),
                "frequency": float(args.frequency),
                "harmonic_sets": harmonic_sets,
                "regions": rows,
            },
            f,
            indent=2,
        )

    write_csv(csv_path, rows)

    print("=== Symatics Phase Map Complete ===")
    print(f"JSON: {json_path}")
    print(f"CSV : {csv_path}")
    print()
    print("Top ranked symbolic regions:")
    for row in rows[: max(1, args.top_k)]:
        print(
            f"phi={row['phi']:.6f} | deg={row['phi_deg']:.2f} | "
            f"harmonics={row['harmonics']} | state={row['semantic_state']} | "
            f"locked={row['locked']} | drift={row['drift']:.6f} | "
            f"stability={row['stability_mean']:.6f} | pickup={row['pickup_mean']:.6f} | "
            f"quality={row['quality']:.6f}"
        )

    if hasattr(engine, "emitter") and hasattr(engine.emitter, "field_bridge"):
        fb = engine.emitter.field_bridge
        if hasattr(fb, "shutdown"):
            fb.shutdown()


if __name__ == "__main__":
    main()