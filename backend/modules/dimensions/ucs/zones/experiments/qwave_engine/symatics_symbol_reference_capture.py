from __future__ import annotations

"""
Symatics Symbol Reference Capture
---------------------------------
Build clean reference profiles for approved Tier-1 symbols.

Purpose
- run repeated captures for selected symbols
- compile each symbol through the field compiler
- dwell for a fixed number of ticks per capture
- aggregate repeated observations into canonical reference statistics
- produce a production-oriented reference catalog for decoder calibration

Typical usage
-------------
PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/symatics_symbol_reference_capture.py \
  --catalog backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_catalog.json \
  --symbols S1 S2 S4 \
  --captures 20 \
  --ticks 40 \
  --safe-mode

Outputs
- symatics_symbol_reference_capture_report.json
- symatics_symbol_reference_capture_report.csv
- symatics_symbol_reference_catalog.json
"""

import argparse
import csv
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

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
DEFAULT_JSON_OUT = OUTPUT_DIR / "symatics_symbol_reference_capture_report.json"
DEFAULT_CSV_OUT = OUTPUT_DIR / "symatics_symbol_reference_capture_report.csv"
DEFAULT_REFERENCE_CATALOG_OUT = OUTPUT_DIR / "symatics_symbol_reference_catalog.json"

TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if value is None:
        return default
    return bool(value)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _phase_distance(a: float, b: float) -> float:
    a = _wrap_phase(a)
    b = _wrap_phase(b)
    d = abs(a - b)
    return min(d, TWO_PI - d)


def _circular_mean(phases: Sequence[float]) -> float:
    if not phases:
        return 0.0
    s = sum(math.sin(_wrap_phase(p)) for p in phases)
    c = sum(math.cos(_wrap_phase(p)) for p in phases)
    if abs(s) < 1e-12 and abs(c) < 1e-12:
        return _wrap_phase(phases[0])
    return _wrap_phase(math.atan2(s, c))


def _circular_std(phases: Sequence[float]) -> float:
    if len(phases) < 2:
        return 0.0
    mu = _circular_mean(phases)
    var = sum(_phase_distance(p, mu) ** 2 for p in phases) / len(phases)
    return math.sqrt(var)


def _parse_harmonics(value: Any) -> List[int]:
    if value is None:
        return [1]

    if isinstance(value, list):
        out: List[int] = []
        for item in value:
            try:
                out.append(max(1, int(item)))
            except Exception:
                pass
        return out or [1]

    text = str(value).strip()
    if not text:
        return [1]

    if text.startswith("[") and text.endswith("]"):
        try:
            data = json.loads(text)
            return _parse_harmonics(data)
        except Exception:
            pass

    out: List[int] = []
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            out.append(max(1, int(float(token))))
        except Exception:
            pass
    return out or [1]


# ---------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------
@dataclass(slots=True)
class CatalogSymbol:
    symbol_id: str
    name: str
    semantic_state: str
    phi: float
    harmonics: List[int]
    stability: float
    lock_quality: float
    drift: float
    mean_pickup: float
    pickup_std: float
    voltage_mean: float
    ticks: int
    locked: bool
    rank_score: float
    notes: Dict[str, Any]


@dataclass(slots=True)
class CaptureObservation:
    symbol_id: str
    symbol_name: str
    semantic_state: str
    capture_index: int
    phi_hint: float
    harmonics_hint: List[int]
    stability_mean: float
    drift: float
    voltage_mean: float
    pickup_mean: float
    pickup_std: float
    aux_adc_1_mean: float
    aux_adc_2_mean: float
    magnetometer_x_mean: float
    magnetometer_y_mean: float
    magnetometer_z_mean: float
    ticks: int
    locked: bool


@dataclass(slots=True)
class SymbolReferenceSummary:
    symbol_id: str
    symbol_name: str
    semantic_state: str
    captures: int
    phi: float
    harmonics: List[int]
    stability_mean: float
    stability_std: float
    drift_mean: float
    drift_std: float
    voltage_mean: float
    voltage_std: float
    pickup_mean: float
    pickup_std: float
    pickup_capture_std: float
    aux_adc_1_mean: float
    aux_adc_1_std: float
    aux_adc_2_mean: float
    aux_adc_2_std: float
    magnetometer_x_mean: float
    magnetometer_x_std: float
    magnetometer_y_mean: float
    magnetometer_y_std: float
    magnetometer_z_mean: float
    magnetometer_z_std: float
    ticks_mean: float
    locked_capture_count: int
    locked_capture_rate: float
    source_rank_score: float
    source_locked: bool
    source_notes: Dict[str, Any]


# ---------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------
def load_catalog(path: Path) -> Dict[str, CatalogSymbol]:
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("symbols"), list):
        rows = payload["symbols"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError(f"Unrecognized catalog format: {path}")

    out: Dict[str, CatalogSymbol] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue

        symbol_id = str(row.get("symbol_id", "")).strip()
        if not symbol_id:
            continue

        notes = row.get("notes")
        if not isinstance(notes, dict):
            notes = {}

        out[symbol_id] = CatalogSymbol(
            symbol_id=symbol_id,
            name=str(row.get("name", symbol_id)),
            semantic_state=str(row.get("semantic_state", "unknown")),
            phi=_wrap_phase(_safe_float(row.get("phi"), 0.0)),
            harmonics=_parse_harmonics(row.get("harmonics")),
            stability=_safe_float(row.get("stability"), 0.0),
            lock_quality=_safe_float(row.get("lock_quality"), 0.0),
            drift=_safe_float(row.get("drift"), 0.0),
            mean_pickup=_safe_float(row.get("mean_pickup"), 0.0),
            pickup_std=_safe_float(row.get("pickup_std"), 0.0),
            voltage_mean=_safe_float(
                row.get("voltage_mean", notes.get("voltage_mean", 0.0)),
                0.0,
            ),
            ticks=_safe_int(row.get("ticks"), 0),
            locked=_safe_bool(row.get("locked"), False),
            rank_score=_safe_float(row.get("rank_score"), 0.0),
            notes=notes,
        )

    if not out:
        raise ValueError(f"No symbols loaded from catalog: {path}")

    return out


# ---------------------------------------------------------------------
# Engine/sensor context
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# Single capture
# ---------------------------------------------------------------------
def run_single_capture(
    engine: Any,
    sensors: SensorBridge,
    field_compiler: SymaticsFieldCompiler,
    symbol: CatalogSymbol,
    capture_index: int,
    ticks: int,
    frequency: float,
    amplitude: float,
    tick_sleep_override: Optional[float] = None,
) -> CaptureObservation:
    program = field_compiler.compile_symbol(
        symbol.symbol_id,
        frequency=frequency,
        amplitude=amplitude,
    )
    expr = program.to_expression(engine.compiler)

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
        snap = sensors.read_all().to_dict()

        phase_vals.append(_wrap_phase(_safe_float(feedback.measured_phase, 0.0)))
        voltage_vals.append(_safe_float(feedback.measured_voltage, 0.0))
        stability_vals.append(_safe_float(feedback.stability_score, 0.0))

        pickup_vals.append(_safe_float(snap.get("pickup_voltage"), 0.0))
        aux1_vals.append(_safe_float(snap.get("aux_adc_1"), 0.0))
        aux2_vals.append(_safe_float(snap.get("aux_adc_2"), 0.0))
        mx_vals.append(_safe_float(snap.get("magnetometer_x"), 0.0))
        my_vals.append(_safe_float(snap.get("magnetometer_y"), 0.0))
        mz_vals.append(_safe_float(snap.get("magnetometer_z"), 0.0))

        locked = locked or bool(getattr(engine, "is_locked", lambda *a, **k: False)())

        sleep_s = (
            tick_sleep_override
            if tick_sleep_override is not None
            else getattr(engine, "tick_delay_s", 0.0)
        )
        if sleep_s and sleep_s > 0:
            time.sleep(sleep_s)

    return CaptureObservation(
        symbol_id=symbol.symbol_id,
        symbol_name=symbol.name,
        semantic_state=symbol.semantic_state,
        capture_index=capture_index,
        phi_hint=symbol.phi,
        harmonics_hint=list(symbol.harmonics),
        stability_mean=_mean(stability_vals),
        drift=_circular_std(phase_vals),
        voltage_mean=_mean(voltage_vals),
        pickup_mean=_mean(pickup_vals),
        pickup_std=_std(pickup_vals),
        aux_adc_1_mean=_mean(aux1_vals),
        aux_adc_2_mean=_mean(aux2_vals),
        magnetometer_x_mean=_mean(mx_vals),
        magnetometer_y_mean=_mean(my_vals),
        magnetometer_z_mean=_mean(mz_vals),
        ticks=ticks,
        locked=locked,
    )


# ---------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------
def summarize_symbol_captures(
    symbol: CatalogSymbol,
    captures: List[CaptureObservation],
) -> SymbolReferenceSummary:
    stabilities = [x.stability_mean for x in captures]
    drifts = [x.drift for x in captures]
    voltages = [x.voltage_mean for x in captures]
    pickups = [x.pickup_mean for x in captures]
    pickup_stds = [x.pickup_std for x in captures]
    aux1s = [x.aux_adc_1_mean for x in captures]
    aux2s = [x.aux_adc_2_mean for x in captures]
    mxs = [x.magnetometer_x_mean for x in captures]
    mys = [x.magnetometer_y_mean for x in captures]
    mzs = [x.magnetometer_z_mean for x in captures]
    ticks = [float(x.ticks) for x in captures]
    locked_count = sum(1 for x in captures if x.locked)

    return SymbolReferenceSummary(
        symbol_id=symbol.symbol_id,
        symbol_name=symbol.name,
        semantic_state=symbol.semantic_state,
        captures=len(captures),
        phi=symbol.phi,
        harmonics=list(symbol.harmonics),
        stability_mean=_mean(stabilities),
        stability_std=_std(stabilities),
        drift_mean=_mean(drifts),
        drift_std=_std(drifts),
        voltage_mean=_mean(voltages),
        voltage_std=_std(voltages),
        pickup_mean=_mean(pickups),
        pickup_std=_mean(pickup_stds),
        pickup_capture_std=_std(pickups),
        aux_adc_1_mean=_mean(aux1s),
        aux_adc_1_std=_std(aux1s),
        aux_adc_2_mean=_mean(aux2s),
        aux_adc_2_std=_std(aux2s),
        magnetometer_x_mean=_mean(mxs),
        magnetometer_x_std=_std(mxs),
        magnetometer_y_mean=_mean(mys),
        magnetometer_y_std=_std(mys),
        magnetometer_z_mean=_mean(mzs),
        magnetometer_z_std=_std(mzs),
        ticks_mean=_mean(ticks),
        locked_capture_count=locked_count,
        locked_capture_rate=(locked_count / len(captures)) if captures else 0.0,
        source_rank_score=symbol.rank_score,
        source_locked=symbol.locked,
        source_notes=dict(symbol.notes),
    )


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------
def write_report_json(
    path: Path,
    catalog_path: Path,
    symbols: List[str],
    captures_per_symbol: int,
    ticks_per_capture: int,
    observations: List[CaptureObservation],
    summaries: List[SymbolReferenceSummary],
) -> None:
    payload = {
        "catalog": str(catalog_path),
        "symbols_tested": symbols,
        "captures_per_symbol": captures_per_symbol,
        "ticks_per_capture": ticks_per_capture,
        "capture_count": len(observations),
        "summaries": [asdict(x) for x in summaries],
        "captures": [asdict(x) for x in observations],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_report_csv(path: Path, observations: List[CaptureObservation]) -> None:
    fieldnames = [
        "symbol_id",
        "symbol_name",
        "semantic_state",
        "capture_index",
        "phi_hint",
        "harmonics_hint",
        "stability_mean",
        "drift",
        "voltage_mean",
        "pickup_mean",
        "pickup_std",
        "aux_adc_1_mean",
        "aux_adc_2_mean",
        "magnetometer_x_mean",
        "magnetometer_y_mean",
        "magnetometer_z_mean",
        "ticks",
        "locked",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in observations:
            payload = asdict(row)
            payload["harmonics_hint"] = json.dumps(payload["harmonics_hint"])
            payload["phi_hint"] = f"{row.phi_hint:.9f}"
            payload["stability_mean"] = f"{row.stability_mean:.6f}"
            payload["drift"] = f"{row.drift:.6f}"
            payload["voltage_mean"] = f"{row.voltage_mean:.6f}"
            payload["pickup_mean"] = f"{row.pickup_mean:.6f}"
            payload["pickup_std"] = f"{row.pickup_std:.6f}"
            payload["aux_adc_1_mean"] = f"{row.aux_adc_1_mean:.6f}"
            payload["aux_adc_2_mean"] = f"{row.aux_adc_2_mean:.6f}"
            payload["magnetometer_x_mean"] = f"{row.magnetometer_x_mean:.6f}"
            payload["magnetometer_y_mean"] = f"{row.magnetometer_y_mean:.6f}"
            payload["magnetometer_z_mean"] = f"{row.magnetometer_z_mean:.6f}"
            writer.writerow(payload)


def write_reference_catalog_json(
    path: Path,
    catalog_path: Path,
    summaries: List[SymbolReferenceSummary],
) -> None:
    symbols: List[Dict[str, Any]] = []
    for s in summaries:
        symbols.append(
            {
                "symbol_id": s.symbol_id,
                "name": s.symbol_name,
                "semantic_state": s.semantic_state,
                "phi": s.phi,
                "phi_deg": math.degrees(s.phi),
                "harmonics": list(s.harmonics),
                "stability": s.stability_mean,
                "stability_std": s.stability_std,
                "lock_quality": 0.0,
                "drift": s.drift_mean,
                "drift_std": s.drift_std,
                "mean_pickup": s.pickup_mean,
                "pickup_std": s.pickup_capture_std,
                "voltage_mean": s.voltage_mean,
                "voltage_std": s.voltage_std,
                "ticks": int(round(s.ticks_mean)),
                "locked": s.locked_capture_rate >= 0.5,
                "rank_score": s.source_rank_score,
                "notes": {
                    **dict(s.source_notes),
                    "reference_capture_mode": True,
                    "reference_capture_count": s.captures,
                    "reference_locked_capture_count": s.locked_capture_count,
                    "reference_locked_capture_rate": s.locked_capture_rate,
                    "aux_adc_1_mean": s.aux_adc_1_mean,
                    "aux_adc_1_std": s.aux_adc_1_std,
                    "aux_adc_2_mean": s.aux_adc_2_mean,
                    "aux_adc_2_std": s.aux_adc_2_std,
                    "magnetometer_x_mean": s.magnetometer_x_mean,
                    "magnetometer_x_std": s.magnetometer_x_std,
                    "magnetometer_y_mean": s.magnetometer_y_mean,
                    "magnetometer_y_std": s.magnetometer_y_std,
                    "magnetometer_z_mean": s.magnetometer_z_mean,
                    "magnetometer_z_std": s.magnetometer_z_std,
                    "source_catalog": str(catalog_path),
                },
            }
        )

    payload = {
        "source_catalog": str(catalog_path),
        "symbol_count": len(symbols),
        "symbols": symbols,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture repeated reference profiles for approved Symatics symbols"
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG_PATH),
        help="Path to symatics_symbol_catalog.json",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Catalog symbol IDs to capture, e.g. S1 S2 S4",
    )
    parser.add_argument(
        "--captures",
        type=int,
        default=20,
        help="Number of repeated captures per symbol",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=40,
        help="Ticks per capture",
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=1.0,
        help="Base frequency scalar passed to field compiler",
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        default=1.0,
        help="Base amplitude passed to field compiler",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Use safe/simulated hardware mode",
    )
    parser.add_argument(
        "--tick-sleep",
        type=float,
        default=None,
        help="Optional override sleep per tick in seconds",
    )
    parser.add_argument(
        "--json-out",
        default=str(DEFAULT_JSON_OUT),
        help="JSON report output path",
    )
    parser.add_argument(
        "--csv-out",
        default=str(DEFAULT_CSV_OUT),
        help="Per-capture CSV output path",
    )
    parser.add_argument(
        "--reference-catalog-out",
        default=str(DEFAULT_REFERENCE_CATALOG_OUT),
        help="Reference catalog JSON output path",
    )
    return parser


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    args = build_parser().parse_args()

    catalog_path = Path(args.catalog)
    json_out = Path(args.json_out)
    csv_out = Path(args.csv_out)
    reference_catalog_out = Path(args.reference_catalog_out)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    reference_catalog_out.parent.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog(catalog_path)

    missing = [sid for sid in args.symbols if sid not in catalog]
    if missing:
        raise SystemExit(f"Unknown symbol IDs: {missing}")

    engine = build_hello_world_engine(safe_mode=args.safe_mode)
    sensors = SensorBridge(safe_mode=args.safe_mode)
    field_compiler = SymaticsFieldCompiler(catalog_path)

    observations: List[CaptureObservation] = []
    summaries: List[SymbolReferenceSummary] = []

    try:
        for symbol_id in args.symbols:
            symbol = catalog[symbol_id]
            symbol_captures: List[CaptureObservation] = []

            for capture_index in range(1, args.captures + 1):
                obs = run_single_capture(
                    engine=engine,
                    sensors=sensors,
                    field_compiler=field_compiler,
                    symbol=symbol,
                    capture_index=capture_index,
                    ticks=args.ticks,
                    frequency=args.frequency,
                    amplitude=args.amplitude,
                    tick_sleep_override=args.tick_sleep,
                )
                symbol_captures.append(obs)
                observations.append(obs)

            summaries.append(summarize_symbol_captures(symbol, symbol_captures))

    finally:
        shutdown = getattr(engine, "shutdown", None)
        if callable(shutdown):
            shutdown()

    write_report_json(
        path=json_out,
        catalog_path=catalog_path,
        symbols=args.symbols,
        captures_per_symbol=args.captures,
        ticks_per_capture=args.ticks,
        observations=observations,
        summaries=summaries,
    )
    write_report_csv(csv_out, observations)
    write_reference_catalog_json(reference_catalog_out, catalog_path, summaries)

    print("=== Symatics Symbol Reference Capture ===")
    print(f"Catalog          : {catalog_path}")
    print(f"Symbols tested   : {args.symbols}")
    print(f"Captures/symbol  : {args.captures}")
    print(f"Ticks/capture    : {args.ticks}")
    print()

    for s in summaries:
        print(
            f"{s.symbol_id} | {s.semantic_state} | "
            f"captures={s.captures} | "
            f"pickup={s.pickup_mean:.6f}±{s.pickup_capture_std:.6f} | "
            f"stability={s.stability_mean:.6f}±{s.stability_std:.6f} | "
            f"drift={s.drift_mean:.6f}±{s.drift_std:.6f} | "
            f"locked_rate={s.locked_capture_rate:.6f}"
        )

    print()
    print(f"JSON             : {json_out}")
    print(f"CSV              : {csv_out}")
    print(f"Reference Catalog: {reference_catalog_out}")


if __name__ == "__main__":
    main()