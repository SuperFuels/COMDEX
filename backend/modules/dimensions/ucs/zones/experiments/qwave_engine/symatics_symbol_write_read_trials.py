from __future__ import annotations

"""
Symatics Symbol Write/Read Trials
---------------------------------
Run repeated write/read trials for catalog symbols.

Purpose
- select one or more canonical symbols from symatics_symbol_catalog.json
- emit each symbol repeatedly through the Symatics engine
- capture each run as an observation vector
- decode each observation back against the catalog
- measure:
    * exact agreement rate
    * semantic agreement rate
    * mean confidence
    * mean runner-up margin
    * confusion pairs
    * per-trial outcomes

This is the reliability layer after:
- catalog construction
- decoder construction
- single-capture validation

Typical usage
-------------
Run 20 trials each for S1, S2, and S4 in safe mode:

    PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/symatics_symbol_write_read_trials.py \
      --safe-mode \
      --symbols S1 S2 S4 \
      --trials 20 \
      --ticks 40

Outputs
- symatics_symbol_write_read_trials_report.json
- symatics_symbol_write_read_trials_report.csv
- symatics_symbol_write_read_trials_confusion_matrix.csv
"""

import argparse
import csv
import json
import math
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.sensor_bridge import (
    SensorBridge,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_field_compiler import (
    SymaticsFieldCompiler,
)
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_symbol_decoder import (
    ObservationVector,
    SymaticsSymbolDecoder,
)

OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

DEFAULT_CATALOG_PATH = OUTPUT_DIR / "symatics_symbol_catalog.json"
DEFAULT_JSON_OUT = OUTPUT_DIR / "symatics_symbol_write_read_trials_report.json"
DEFAULT_CSV_OUT = OUTPUT_DIR / "symatics_symbol_write_read_trials_report.csv"
DEFAULT_MATRIX_OUT = OUTPUT_DIR / "symatics_symbol_write_read_trials_confusion_matrix.csv"

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
    locked: bool
    notes: Dict[str, Any]


@dataclass(slots=True)
class TrialResult:
    expected_symbol_id: str
    expected_name: str
    expected_semantic_state: str
    trial_index: int
    predicted_symbol_id: str
    predicted_name: str
    predicted_semantic_state: str
    confidence: float
    runner_up_symbol_id: str
    runner_up_name: str
    margin: float
    agreed_symbol: bool
    agreed_semantic: bool
    pickup_mean: float
    stability_mean: float
    drift: float
    locked: bool


@dataclass(slots=True)
class SymbolTrialSummary:
    symbol_id: str
    symbol_name: str
    semantic_state: str
    trials: int
    exact_hits: int
    semantic_hits: int
    exact_accuracy: float
    semantic_accuracy: float
    mean_confidence: float
    min_confidence: float
    max_confidence: float
    mean_margin: float
    mean_pickup: float
    mean_stability: float
    mean_drift: float
    most_common_confusion_symbol: str
    confusion_count: int


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
            locked=_safe_bool(row.get("locked"), False),
            notes=notes,
        )

    if not out:
        raise ValueError(f"No symbols loaded from catalog: {path}")

    return out


# ---------------------------------------------------------------------
# Observation building
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


def _build_observation_from_trial(
    expected_symbol: CatalogSymbol,
    trial_index: int,
    phase_vals: List[float],
    voltage_vals: List[float],
    stability_vals: List[float],
    pickup_vals: List[float],
    aux1_vals: List[float],
    aux2_vals: List[float],
    mx_vals: List[float],
    my_vals: List[float],
    mz_vals: List[float],
    locked: bool,
    ticks: int,
) -> ObservationVector:
    return ObservationVector(
        source_name=f"{expected_symbol.symbol_id}_trial_{trial_index}",
        source_kind="write_read_trial",
        semantic_hint=expected_symbol.semantic_state,
        phi_hint=expected_symbol.phi,
        harmonics_hint=list(expected_symbol.harmonics),
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
        metadata={
            "expected_symbol_id": expected_symbol.symbol_id,
            "expected_name": expected_symbol.name,
        },
    )


# ---------------------------------------------------------------------
# Trial execution
# ---------------------------------------------------------------------
def run_single_trial(
    engine: Any,
    sensors: SensorBridge,
    field_compiler: SymaticsFieldCompiler,
    expected_symbol: CatalogSymbol,
    trial_index: int,
    ticks: int,
    tick_sleep_override: Optional[float] = None,
) -> ObservationVector:
    program = field_compiler.compile_symbol(
        expected_symbol.symbol_id,
        frequency=1.0,
        amplitude=1.0,
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

        sleep_s = (
            tick_sleep_override
            if tick_sleep_override is not None
            else getattr(engine, "tick_delay_s", 0.0)
        )
        if sleep_s and sleep_s > 0:
            time.sleep(sleep_s)

    return _build_observation_from_trial(
        expected_symbol=expected_symbol,
        trial_index=trial_index,
        phase_vals=phase_vals,
        voltage_vals=voltage_vals,
        stability_vals=stability_vals,
        pickup_vals=pickup_vals,
        aux1_vals=aux1_vals,
        aux2_vals=aux2_vals,
        mx_vals=mx_vals,
        my_vals=my_vals,
        mz_vals=mz_vals,
        locked=locked,
        ticks=ticks,
    )


# ---------------------------------------------------------------------
# Decode integration
# ---------------------------------------------------------------------
def decode_trial_observation(
    decoder: SymaticsSymbolDecoder,
    observation: ObservationVector,
    top_k: int = 5,
) -> Dict[str, Any]:
    result = decoder.decode_observation(observation, top_k=top_k)
    return asdict(result)


def build_trial_result(
    expected_symbol: CatalogSymbol,
    trial_index: int,
    observation: ObservationVector,
    decoded: Dict[str, Any],
) -> TrialResult:
    top_matches = decoded.get("top_matches", [])
    best = top_matches[0] if top_matches else {}

    predicted_symbol_id = str(
        decoded.get("predicted_symbol_id", best.get("symbol_id", ""))
    )
    predicted_name = str(decoded.get("predicted_name", best.get("name", "")))
    predicted_semantic_state = str(
        decoded.get("predicted_semantic_state", best.get("semantic_state", ""))
    )
    confidence = _safe_float(
        decoded.get("confidence", best.get("confidence", 0.0)),
        0.0,
    )

    runner_up_symbol_id = str(decoded.get("runner_up_symbol_id", ""))
    runner_up_name = str(decoded.get("runner_up_name", ""))
    margin = _safe_float(decoded.get("margin", 0.0), 0.0)

    agreed_symbol = predicted_symbol_id == expected_symbol.symbol_id
    agreed_semantic = predicted_semantic_state == expected_symbol.semantic_state

    return TrialResult(
        expected_symbol_id=expected_symbol.symbol_id,
        expected_name=expected_symbol.name,
        expected_semantic_state=expected_symbol.semantic_state,
        trial_index=trial_index,
        predicted_symbol_id=predicted_symbol_id,
        predicted_name=predicted_name,
        predicted_semantic_state=predicted_semantic_state,
        confidence=confidence,
        runner_up_symbol_id=runner_up_symbol_id,
        runner_up_name=runner_up_name,
        margin=margin,
        agreed_symbol=agreed_symbol,
        agreed_semantic=agreed_semantic,
        pickup_mean=observation.pickup_mean,
        stability_mean=observation.stability_mean,
        drift=observation.drift,
        locked=observation.locked,
    )


# ---------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------
def summarize_symbol_trials(results: List[TrialResult]) -> List[SymbolTrialSummary]:
    grouped: Dict[str, List[TrialResult]] = defaultdict(list)
    for result in results:
        grouped[result.expected_symbol_id].append(result)

    summaries: List[SymbolTrialSummary] = []
    for symbol_id, items in grouped.items():
        exact_hits = sum(1 for item in items if item.agreed_symbol)
        semantic_hits = sum(1 for item in items if item.agreed_semantic)
        confidences = [item.confidence for item in items]
        margins = [item.margin for item in items]
        pickups = [item.pickup_mean for item in items]
        stabilities = [item.stability_mean for item in items]
        drifts = [item.drift for item in items]

        confusion_counts: Dict[str, int] = defaultdict(int)
        for item in items:
            if not item.agreed_symbol and item.predicted_symbol_id:
                confusion_counts[item.predicted_symbol_id] += 1

        most_common_confusion_symbol = ""
        confusion_count = 0
        if confusion_counts:
            most_common_confusion_symbol, confusion_count = max(
                confusion_counts.items(),
                key=lambda kv: kv[1],
            )

        exemplar = items[0]
        summaries.append(
            SymbolTrialSummary(
                symbol_id=symbol_id,
                symbol_name=exemplar.expected_name,
                semantic_state=exemplar.expected_semantic_state,
                trials=len(items),
                exact_hits=exact_hits,
                semantic_hits=semantic_hits,
                exact_accuracy=(exact_hits / len(items)) if items else 0.0,
                semantic_accuracy=(semantic_hits / len(items)) if items else 0.0,
                mean_confidence=_mean(confidences),
                min_confidence=min(confidences) if confidences else 0.0,
                max_confidence=max(confidences) if confidences else 0.0,
                mean_margin=_mean(margins),
                mean_pickup=_mean(pickups),
                mean_stability=_mean(stabilities),
                mean_drift=_mean(drifts),
                most_common_confusion_symbol=most_common_confusion_symbol,
                confusion_count=confusion_count,
            )
        )

    summaries.sort(key=lambda x: x.symbol_id)
    return summaries


def build_confusion_matrix(
    results: List[TrialResult],
) -> Tuple[List[str], Dict[str, Dict[str, int]]]:
    labels = sorted(
        set(item.expected_symbol_id for item in results).union(
            set(item.predicted_symbol_id for item in results if item.predicted_symbol_id)
        )
    )
    matrix: Dict[str, Dict[str, int]] = {
        row: {col: 0 for col in labels}
        for row in labels
    }

    for item in results:
        if item.expected_symbol_id and item.predicted_symbol_id:
            matrix[item.expected_symbol_id][item.predicted_symbol_id] += 1

    return labels, matrix


def overall_metrics(results: List[TrialResult]) -> Dict[str, Any]:
    exact_hits = sum(1 for item in results if item.agreed_symbol)
    semantic_hits = sum(1 for item in results if item.agreed_semantic)

    return {
        "trials_total": len(results),
        "exact_hits": exact_hits,
        "semantic_hits": semantic_hits,
        "exact_accuracy": (exact_hits / len(results)) if results else 0.0,
        "semantic_accuracy": (semantic_hits / len(results)) if results else 0.0,
        "mean_confidence": _mean([item.confidence for item in results]),
        "mean_margin": _mean([item.margin for item in results]),
    }


# ---------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------
def write_report_json(
    path: Path,
    catalog_path: Path,
    symbols: List[str],
    trials_per_symbol: int,
    results: List[TrialResult],
    summaries: List[SymbolTrialSummary],
    labels: List[str],
    matrix: Dict[str, Dict[str, int]],
    metrics: Dict[str, Any],
) -> None:
    payload = {
        "catalog": str(catalog_path),
        "symbols_tested": symbols,
        "trials_per_symbol": trials_per_symbol,
        "overall_metrics": metrics,
        "per_symbol_summary": [asdict(x) for x in summaries],
        "confusion_matrix": {
            "labels": labels,
            "rows": matrix,
        },
        "trials": [asdict(x) for x in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_trials_csv(path: Path, results: List[TrialResult]) -> None:
    fieldnames = [
        "expected_symbol_id",
        "expected_name",
        "expected_semantic_state",
        "trial_index",
        "predicted_symbol_id",
        "predicted_name",
        "predicted_semantic_state",
        "confidence",
        "runner_up_symbol_id",
        "runner_up_name",
        "margin",
        "agreed_symbol",
        "agreed_semantic",
        "pickup_mean",
        "stability_mean",
        "drift",
        "locked",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "expected_symbol_id": item.expected_symbol_id,
                    "expected_name": item.expected_name,
                    "expected_semantic_state": item.expected_semantic_state,
                    "trial_index": item.trial_index,
                    "predicted_symbol_id": item.predicted_symbol_id,
                    "predicted_name": item.predicted_name,
                    "predicted_semantic_state": item.predicted_semantic_state,
                    "confidence": f"{item.confidence:.6f}",
                    "runner_up_symbol_id": item.runner_up_symbol_id,
                    "runner_up_name": item.runner_up_name,
                    "margin": f"{item.margin:.6f}",
                    "agreed_symbol": item.agreed_symbol,
                    "agreed_semantic": item.agreed_semantic,
                    "pickup_mean": f"{item.pickup_mean:.6f}",
                    "stability_mean": f"{item.stability_mean:.6f}",
                    "drift": f"{item.drift:.6f}",
                    "locked": item.locked,
                }
            )


def write_confusion_matrix_csv(
    path: Path,
    labels: List[str],
    matrix: Dict[str, Dict[str, int]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["expected \\ predicted", *labels])
        for row_label in labels:
            writer.writerow([row_label, *[matrix[row_label][col] for col in labels]])


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run repeated Symatics write/read trials for selected catalog symbols"
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
        help="Catalog symbol IDs to trial, e.g. S1 S2 S4",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=20,
        help="Number of repeated trials per symbol",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=40,
        help="Ticks per trial capture",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Use safe/simulated hardware mode",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Decoder top-k ranking depth",
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
        help="Per-trial CSV output path",
    )
    parser.add_argument(
        "--matrix-out",
        default=str(DEFAULT_MATRIX_OUT),
        help="Confusion matrix CSV output path",
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
    matrix_out = Path(args.matrix_out)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    matrix_out.parent.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog(catalog_path)
    requested_symbols = args.symbols

    missing = [sid for sid in requested_symbols if sid not in catalog]
    if missing:
        raise SystemExit(f"Unknown symbol IDs: {missing}")

    engine = build_hello_world_engine(safe_mode=args.safe_mode)
    sensors = SensorBridge(safe_mode=args.safe_mode)
    decoder = SymaticsSymbolDecoder(catalog_path)
    field_compiler = SymaticsFieldCompiler(catalog_path)

    results: List[TrialResult] = []

    try:
        for symbol_id in requested_symbols:
            expected_symbol = catalog[symbol_id]

            for trial_index in range(1, args.trials + 1):
                observation = run_single_trial(
                    engine=engine,
                    sensors=sensors,
                    field_compiler=field_compiler,
                    expected_symbol=expected_symbol,
                    trial_index=trial_index,
                    ticks=args.ticks,
                    tick_sleep_override=args.tick_sleep,
                )

                decoded = decode_trial_observation(
                    decoder=decoder,
                    observation=observation,
                    top_k=args.top_k,
                )

                results.append(
                    build_trial_result(
                        expected_symbol=expected_symbol,
                        trial_index=trial_index,
                        observation=observation,
                        decoded=decoded,
                    )
                )

    finally:
        shutdown = getattr(engine, "shutdown", None)
        if callable(shutdown):
            shutdown()

    summaries = summarize_symbol_trials(results)
    labels, matrix = build_confusion_matrix(results)
    metrics = overall_metrics(results)

    write_report_json(
        path=json_out,
        catalog_path=catalog_path,
        symbols=requested_symbols,
        trials_per_symbol=args.trials,
        results=results,
        summaries=summaries,
        labels=labels,
        matrix=matrix,
        metrics=metrics,
    )
    write_trials_csv(csv_out, results)
    write_confusion_matrix_csv(matrix_out, labels, matrix)

    print("=== Symatics Symbol Write/Read Trials ===")
    print(f"Catalog         : {catalog_path}")
    print(f"Symbols tested  : {requested_symbols}")
    print(f"Trials/symbol   : {args.trials}")
    print(f"Ticks/trial     : {args.ticks}")
    print()

    for summary in summaries:
        print(
            f"{summary.symbol_id} | {summary.semantic_state} | "
            f"{summary.exact_hits}/{summary.trials} exact | "
            f"{summary.semantic_hits}/{summary.trials} semantic | "
            f"mean_conf={summary.mean_confidence:.6f} | "
            f"mean_margin={summary.mean_margin:.6f} | "
            f"mean_pickup={summary.mean_pickup:.6f} | "
            f"mean_stability={summary.mean_stability:.6f} | "
            f"mean_drift={summary.mean_drift:.6f}"
        )
        if summary.most_common_confusion_symbol:
            print(
                f"  confusion -> {summary.most_common_confusion_symbol} "
                f"({summary.confusion_count} times)"
            )

    print()
    print(
        f"Overall: exact_accuracy={metrics['exact_accuracy']:.6f} | "
        f"semantic_accuracy={metrics['semantic_accuracy']:.6f} | "
        f"mean_confidence={metrics['mean_confidence']:.6f} | "
        f"mean_margin={metrics['mean_margin']:.6f}"
    )
    print()
    print(f"JSON   : {json_out}")
    print(f"CSV    : {csv_out}")
    print(f"Matrix : {matrix_out}")


if __name__ == "__main__":
    main()