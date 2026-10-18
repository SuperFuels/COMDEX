from __future__ import annotations

"""
Symatics Capture
----------------
Emit a single Symatics symbol/program while recording:

- requested symbolic program
- runtime-refined profile
- internal engine feedback
- external sensor bridge channels
- engine lock/drift state

Output
- backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_capture_<timestamp>.jsonl

Notes
- Uses timezone-aware UTC timestamps.
- Supports either:
    1) direct phase/harmonics probe arguments, or
    2) symbol-based capture through SymaticsFieldCompiler
- Symbol mode is the preferred operational path for Tier-1 captures.
"""

import argparse
import json
import time
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.sensor_bridge import SensorBridge
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_field_compiler import (
    SymaticsFieldCompiler,
)

OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)
DEFAULT_CATALOG_PATH = OUTPUT_DIR / "symatics_symbol_catalog.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture Symatics emission + external sensor response"
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Use safe/simulated hardware",
    )

    # Preferred operational path
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG_PATH),
        help="Catalog path used by SymaticsFieldCompiler in symbol mode",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="",
        help="Optional symbol ID to capture via SymaticsFieldCompiler, e.g. S1 S2 S4",
    )

    # Direct probe path
    parser.add_argument(
        "--phi",
        type=float,
        default=0.0,
        help="Phase state in radians (used when --symbol is not supplied)",
    )
    parser.add_argument(
        "--harmonics",
        type=int,
        nargs="+",
        default=[1, 2],
        help="Harmonic stack (used when --symbol is not supplied)",
    )

    parser.add_argument(
        "--amplitude",
        type=float,
        default=1.0,
        help="Symbolic amplitude",
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=1.0,
        help="Symbolic frequency scalar",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=40,
        help="Number of capture ticks",
    )
    parser.add_argument(
        "--duty-cycle",
        type=float,
        default=0.5,
        help="Duty cycle 0..1 (direct probe mode override only)",
    )
    parser.add_argument(
        "--envelope",
        type=str,
        default="steady",
        help="Envelope mode (direct probe mode override only)",
    )
    parser.add_argument(
        "--tick-delay",
        type=float,
        default=None,
        help="Override engine tick delay in seconds",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="capture_probe",
        help="Optional explicit label/name override",
    )
    return parser


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]

    return value


def profile_to_context(profile: Any) -> Dict[str, Any]:
    if profile is None:
        return {}

    metadata = getattr(profile, "metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "label": str(getattr(profile, "label", "")),
        "phi": float(getattr(profile, "phi", 0.0)),
        "amplitude": float(getattr(profile, "amplitude", 1.0)),
        "frequency": float(getattr(profile, "frequency", 1.0)),
        "harmonics": [int(h) for h in getattr(profile, "harmonics", [1])],
        "duty_cycle": float(getattr(profile, "duty_cycle", 0.5)),
        "envelope": str(getattr(profile, "envelope", "steady")),
        "duration_s": float(getattr(profile, "duration_s", 0.0)),
        "interference_factor": float(getattr(profile, "interference_factor", 0.0)),
        "metadata": _json_safe(dict(metadata)),
    }


def feedback_to_dict(feedback: Any) -> Dict[str, Any]:
    if feedback is None:
        return {}
    notes = getattr(feedback, "notes", {})
    if not isinstance(notes, dict):
        notes = {}
    return {
        "measured_voltage": float(getattr(feedback, "measured_voltage", 0.0)),
        "measured_phase": float(getattr(feedback, "measured_phase", 0.0)),
        "measured_amplitude": float(getattr(feedback, "measured_amplitude", 0.0)),
        "measured_frequency": float(getattr(feedback, "measured_frequency", 0.0)),
        "stability_score": float(getattr(feedback, "stability_score", 0.0)),
        "notes": _json_safe(dict(notes)),
    }


def expression_to_dict(expr: Any) -> Dict[str, Any]:
    metadata = getattr(expr, "metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "name": str(getattr(expr, "name", "")),
        "mode": str(getattr(expr, "mode", "")),
        "phi": float(getattr(expr, "phi", 0.0)),
        "amplitude": float(getattr(expr, "amplitude", 1.0)),
        "frequency": float(getattr(expr, "frequency", 1.0)),
        "harmonics": [int(h) for h in getattr(expr, "harmonics", [1])],
        "duty_cycle": float(getattr(expr, "duty_cycle", 0.5)),
        "envelope": str(getattr(expr, "envelope", "steady")),
        "duration_s": float(getattr(expr, "duration_s", 0.0)),
        "metadata": _json_safe(dict(metadata)),
    }


def engine_summary(engine: Any) -> Dict[str, Any]:
    current_profile = getattr(engine, "current_profile", None)
    feedback_history = getattr(getattr(engine, "stabilizer", None), "feedback_history", None)
    last_feedback = feedback_history[-1] if feedback_history else None

    stabilizer = getattr(engine, "stabilizer", None)
    drift_fn = getattr(stabilizer, "drift", None)
    locked_fn = getattr(stabilizer, "is_locked", None)

    return {
        "tick_count": int(getattr(engine, "tick_count", 0)),
        "current_profile": profile_to_context(current_profile),
        "last_feedback": feedback_to_dict(last_feedback) if last_feedback else {},
        "drift": float(drift_fn()) if callable(drift_fn) else 0.0,
        "locked": bool(locked_fn()) if callable(locked_fn) else False,
        "recent_events": list(getattr(engine, "events", [])[-25:]),
    }


def _build_expression(
    args: argparse.Namespace,
    engine: Any,
) -> tuple[Any, Dict[str, Any]]:
    compiler = engine.compiler

    if args.symbol:
        field_compiler = SymaticsFieldCompiler(Path(args.catalog))
        program = field_compiler.compile_symbol(
            args.symbol,
            frequency=args.frequency,
            amplitude=args.amplitude,
        )
        expr = program.to_expression(compiler)

        if args.label and args.label != "capture_probe":
            expr.name = str(args.label)

        requested = {
            "mode": "symbol",
            "symbol_id": str(args.symbol),
            "catalog": str(Path(args.catalog)),
            "program": _json_safe(asdict(program) if is_dataclass(program) else getattr(program, "__dict__", {})),
        }
        return expr, requested

    expr = compiler.phase_probe(
        phi=args.phi,
        frequency=args.frequency,
        amplitude=args.amplitude,
        harmonics=args.harmonics,
    )
    expr.name = str(args.label)
    expr.duty_cycle = float(args.duty_cycle)
    expr.envelope = str(args.envelope)

    requested = {
        "mode": "direct_probe",
        "phi": float(args.phi),
        "frequency": float(args.frequency),
        "amplitude": float(args.amplitude),
        "harmonics": [int(h) for h in args.harmonics],
        "duty_cycle": float(args.duty_cycle),
        "envelope": str(args.envelope),
        "label": str(args.label),
    }
    return expr, requested


def main() -> None:
    args = build_parser().parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"symatics_capture_{ts}.jsonl"

    engine = build_hello_world_engine(safe_mode=args.safe_mode)
    if args.tick_delay is not None:
        engine.tick_delay_s = max(0.0, float(args.tick_delay))

    sensors = SensorBridge(safe_mode=args.safe_mode)

    expr, requested_program = _build_expression(args, engine)

    engine.reset_runtime(clear_feedback=True)
    engine.load_expression(expr)

    written_rows = 0

    with output_path.open("w", encoding="utf-8") as f:
        for _ in range(max(1, int(args.ticks))):
            feedback = engine.stabilize_step()
            current_profile = engine.current_profile

            sensors.update_emission_context(profile_to_context(current_profile))
            snapshot = sensors.read_all()

            engine_locked_fn = getattr(engine, "is_locked", None)
            engine_locked = bool(engine_locked_fn()) if callable(engine_locked_fn) else False

            record = {
                "capture_meta": {
                    "capture_timestamp_utc": datetime.now(UTC).isoformat(),
                    "capture_file": str(output_path),
                    "safe_mode": bool(args.safe_mode),
                    "capture_mode": requested_program["mode"],
                },
                "tick": int(getattr(engine, "tick_count", 0)),
                "requested_program": requested_program,
                "expression": expression_to_dict(expr),
                "profile": profile_to_context(current_profile),
                "internal_feedback": feedback_to_dict(feedback),
                "external_sensors": _json_safe(snapshot.to_dict()),
                "engine_state": {
                    "drift": float(engine.stabilizer.drift()),
                    "locked": engine_locked,
                    "tick_delay_s": float(engine.tick_delay_s),
                },
                "locked": engine_locked,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written_rows += 1

            if engine.tick_delay_s > 0:
                time.sleep(engine.tick_delay_s)

    summary = engine_summary(engine)

    print("=== Symatics Capture Complete ===")
    print(f"Output: {output_path}")
    print(f"Ticks  : {written_rows}")
    if args.symbol:
        print(
            f"Mode   : symbol={args.symbol} | amp={args.amplitude:.3f} | "
            f"freq={args.frequency:.3f}"
        )
    else:
        print(
            f"Mode   : phi={args.phi:.6f} | harmonics={args.harmonics} | "
            f"amp={args.amplitude:.3f} | freq={args.frequency:.3f}"
        )
    print(
        f"Lock   : {summary['locked']} | drift={summary['drift']:.6f} | "
        f"final_tick={summary['tick_count']}"
    )


if __name__ == "__main__":
    main()