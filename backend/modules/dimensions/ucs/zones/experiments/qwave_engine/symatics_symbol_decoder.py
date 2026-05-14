from __future__ import annotations

"""
Symatics Symbol Decoder
-----------------------
Decode an observed Symatics response back into the nearest canonical symbol.

Inputs
- Catalog JSON from symatics_symbol_catalog.py
- Either:
    1) one or more capture JSONL files from symatics_capture.py
    2) a response-analysis JSON from symatics_response_analyzer.py
    3) manual feature values from CLI

Outputs
- Console ranking of nearest symbols
- Optional JSON and CSV decode reports

Purpose
- Close the first symbolic read loop
- Compare measured response vectors against catalog symbols
- Return best match, alternatives, and confidence
- Provide a stable class API for validation/runtime imports

Typical usage
-------------
Decode a capture file against the current catalog:

    PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/symatics_symbol_decoder.py \
      --catalog backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_catalog.json \
      --capture backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_capture_20260314T230711Z.jsonl

Decode multiple captures at once:

    PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/symatics_symbol_decoder.py \
      --capture file1.jsonl file2.jsonl file3.jsonl

Decode from manual measurements:

    PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/symatics_symbol_decoder.py \
      --pickup-mean 0.96 \
      --pickup-std 0.02 \
      --voltage-mean 0.98 \
      --stability-mean 0.97 \
      --drift 0.02 \
      --aux-adc-1-mean 0.35 \
      --aux-adc-2-mean 0.36 \
      --magnetometer-x-mean 0.06 \
      --magnetometer-y-mean 0.00 \
      --magnetometer-z-mean -0.01
"""

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

DEFAULT_CATALOG_PATH = OUTPUT_DIR / "symatics_symbol_catalog.json"
DEFAULT_JSON_OUT = OUTPUT_DIR / "symatics_symbol_decoder_report.json"
DEFAULT_CSV_OUT = OUTPUT_DIR / "symatics_symbol_decoder_report.csv"
DEFAULT_CALIBRATION_PATH = OUTPUT_DIR / "symatics_symbol_decoder_calibration.json"

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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


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


def _circular_phase_mean(phases: Sequence[float]) -> float:
    if not phases:
        return 0.0
    sin_sum = sum(math.sin(_wrap_phase(p)) for p in phases)
    cos_sum = sum(math.cos(_wrap_phase(p)) for p in phases)
    if abs(sin_sum) < 1e-12 and abs(cos_sum) < 1e-12:
        return 0.0
    return _wrap_phase(math.atan2(sin_sum, cos_sum))


def _circular_phase_std(phases: Sequence[float]) -> float:
    """
    Circular phase spread on [0, 2π).
    This fixes the constructive-state bug where values near 0 and 2π
    were incorrectly treated as far apart by linear std.
    """
    if len(phases) < 2:
        return 0.0
    mu = _circular_phase_mean(phases)
    deltas = [_phase_distance(p, mu) for p in phases]
    var = sum(d * d for d in deltas) / len(deltas)
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
        part = part.strip()
        if not part:
            continue
        try:
            out.append(max(1, int(float(part))))
        except Exception:
            pass
    return out or [1]


def _harmonics_distance(a: Sequence[int], b: Sequence[int]) -> float:
    sa = set(int(x) for x in a)
    sb = set(int(x) for x in b)
    union = sa | sb
    if not union:
        return 0.0
    inter = sa & sb
    return 1.0 - (len(inter) / len(union))

def _norm_delta(
    observed: float,
    reference_mean: float,
    reference_std: float,
    floor: float = 1e-3,
    cap: float = 6.0,
) -> float:
    """
    Scale-aware normalized delta, but with protection against tiny-std blowups.

    Why:
    - some reference std values are extremely small
    - dividing by tiny stds creates unrealistic penalties
    - cap prevents one feature from dominating the whole match
    """
    scale = max(abs(reference_std), floor)
    value = abs(observed - reference_mean) / scale
    return min(value, cap)

def _default_decoder_weights() -> Dict[str, float]:
    return {
        "W_PICKUP": 2.4,
        "W_VOLTAGE": 0.8,
        "W_STABILITY": 0.6,
        "W_DRIFT": 0.40,
        "W_PHI": 1.5,
        "W_AUX1": 0.20,
        "W_AUX2": 0.20,
        "W_MX": 0.08,
        "W_MY": 0.08,
        "W_MZ": 0.08,
        "W_HARM": 1.1,
    }


def _decoder_weight_floors() -> Dict[str, float]:
    return {
        "W_PICKUP": 1.8,
        "W_VOLTAGE": 1.0,
        "W_STABILITY": 1.2,
        "W_DRIFT": 0.5,
        "W_PHI": 0.9,
        "W_AUX1": 0.1,
        "W_AUX2": 0.1,
        "W_MX": 0.05,
        "W_MY": 0.05,
        "W_MZ": 0.05,
        "W_HARM": 0.8,
    }


def _decoder_weight_caps() -> Dict[str, float]:
    return {
        "W_PICKUP": 3.0,
        "W_VOLTAGE": 2.0,
        "W_STABILITY": 2.0,
        "W_DRIFT": 1.2,
        "W_PHI": 2.0,
        "W_AUX1": 0.4,
        "W_AUX2": 0.4,
        "W_MX": 0.2,
        "W_MY": 0.2,
        "W_MZ": 0.2,
        "W_HARM": 1.4,
    }


def _load_calibrated_decoder_weights(path: Optional[Path]) -> Dict[str, float]:
    defaults = _default_decoder_weights()
    if path is None or not path.exists():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults

    if isinstance(payload, dict) and isinstance(payload.get("weights"), dict):
        payload = payload["weights"]

    if not isinstance(payload, dict):
        return defaults

    floors = _decoder_weight_floors()
    caps = _decoder_weight_caps()
    blended: Dict[str, float] = {}

    blend_alpha = 0.35

    for key, default_value in defaults.items():
        calibrated_value = _safe_float(payload.get(key), default_value)
        mixed_value = ((1.0 - blend_alpha) * default_value) + (blend_alpha * calibrated_value)
        bounded_value = _clamp(mixed_value, floors[key], caps[key])
        blended[key] = bounded_value

    return blended

# ---------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------
@dataclass(slots=True)
class CatalogSymbol:
    symbol_id: str
    name: str
    semantic_state: str
    phi: float
    phi_deg: float
    harmonics: List[int]
    stability: float
    stability_std: float
    lock_quality: float
    drift: float
    drift_std: float
    mean_pickup: float
    pickup_std: float
    pickup_capture_std: float
    voltage_mean: float
    voltage_std: float
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
    ticks: int
    locked: bool
    rank_score: float
    notes: Dict[str, Any]


@dataclass(slots=True)
class ObservationVector:
    source_name: str
    source_kind: str
    semantic_hint: str
    phi_hint: Optional[float]
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
    metadata: Dict[str, Any]


@dataclass(slots=True)
class SymbolMatch:
    symbol_id: str
    name: str
    semantic_state: str
    distance_total: float
    confidence: float
    pickup_delta: float
    voltage_delta: float
    stability_delta: float
    drift_delta: float
    phi_delta: float
    aux_adc_1_delta: float
    aux_adc_2_delta: float
    magnetometer_x_delta: float
    magnetometer_y_delta: float
    magnetometer_z_delta: float
    harmonics_distance: float
    semantic_bonus: float
    rank_score: float


@dataclass(slots=True)
class DecodeResult:
    source_name: str
    source_kind: str
    semantic_hint: str
    predicted_symbol_id: str
    predicted_name: str
    predicted_semantic_state: str
    confidence: float
    runner_up_symbol_id: str
    runner_up_name: str
    margin: float
    observation: Dict[str, Any]
    top_matches: List[Dict[str, Any]]


# ---------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------
def load_catalog(path: Path) -> List[CatalogSymbol]:
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("symbols"), list):
        rows = payload["symbols"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("Catalog JSON must contain a top-level 'symbols' list or be a list")

    catalog: List[CatalogSymbol] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        notes = row.get("notes")
        if not isinstance(notes, dict):
            notes = {}

        phi = _safe_float(row.get("phi"), 0.0)
        phi_deg = _safe_float(
            row.get("phi_deg", row.get("phi_degrees")),
            math.degrees(phi),
        )

        catalog.append(
            CatalogSymbol(
                symbol_id=str(row.get("symbol_id", "")),
                name=str(row.get("name", "")),
                semantic_state=str(row.get("semantic_state", "unknown")),
                phi=phi,
                phi_deg=phi_deg,
                harmonics=_parse_harmonics(row.get("harmonics")),
                stability=_safe_float(row.get("stability", row.get("stability_mean")), 0.0),
                stability_std=_safe_float(row.get("stability_std"), 0.01),
                lock_quality=_safe_float(row.get("lock_quality", row.get("quality")), 0.0),
                drift=_safe_float(row.get("drift", row.get("drift_mean")), 0.0),
                drift_std=_safe_float(row.get("drift_std"), 0.001),
                mean_pickup=_safe_float(row.get("mean_pickup", row.get("pickup_mean")), 0.0),
                pickup_std=_safe_float(row.get("pickup_std"), 0.01),
                pickup_capture_std=_safe_float(row.get("pickup_capture_std", row.get("pickup_std")), 0.01),
                voltage_mean=_safe_float(
                    row.get("voltage_mean", notes.get("voltage_mean", 0.0)),
                    0.0,
                ),
                voltage_std=_safe_float(row.get("voltage_std"), 0.01),
                aux_adc_1_mean=_safe_float(row.get("aux_adc_1_mean", notes.get("aux_adc_1_mean", 0.0)), 0.0),
                aux_adc_1_std=_safe_float(row.get("aux_adc_1_std"), 0.01),
                aux_adc_2_mean=_safe_float(row.get("aux_adc_2_mean", notes.get("aux_adc_2_mean", 0.0)), 0.0),
                aux_adc_2_std=_safe_float(row.get("aux_adc_2_std"), 0.01),
                magnetometer_x_mean=_safe_float(row.get("magnetometer_x_mean", notes.get("magnetometer_x_mean", 0.0)), 0.0),
                magnetometer_x_std=_safe_float(row.get("magnetometer_x_std"), 0.01),
                magnetometer_y_mean=_safe_float(row.get("magnetometer_y_mean", notes.get("magnetometer_y_mean", 0.0)), 0.0),
                magnetometer_y_std=_safe_float(row.get("magnetometer_y_std"), 0.01),
                magnetometer_z_mean=_safe_float(row.get("magnetometer_z_mean", notes.get("magnetometer_z_mean", 0.0)), 0.0),
                magnetometer_z_std=_safe_float(row.get("magnetometer_z_std"), 0.01),
                ticks=_safe_int(row.get("ticks", row.get("ticks_mean")), 0),
                locked=_safe_bool(row.get("locked"), False),
                rank_score=_safe_float(row.get("rank_score", row.get("source_rank_score")), 0.0),
                notes=notes,
            )
        )

    if not catalog:
        raise ValueError(f"No symbols loaded from catalog: {path}")

    return catalog


# ---------------------------------------------------------------------
# Observation loading from capture JSONL
# ---------------------------------------------------------------------
def _extract_capture_observation(path: Path) -> ObservationVector:
    if not path.exists():
        raise FileNotFoundError(f"Capture not found: {path}")

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Capture file is empty: {path}")

    records: List[Dict[str, Any]] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            records.append(payload)

    if not records:
        raise ValueError(f"Capture file has no valid JSON records: {path}")

    # -----------------------------------------------------------------
    # Fast path: flattened ObservationVector-style capture rows
    # Supports one-record JSON/JSONL files produced by candidate sweeps.
    # -----------------------------------------------------------------
    if len(records) == 1:
        rec0 = records[0]
        flat_keys = {
            "source_name",
            "source_kind",
            "semantic_hint",
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
        }

        if isinstance(rec0, dict) and any(k in rec0 for k in flat_keys):
            return ObservationVector(
                source_name=str(rec0.get("source_name", path.name)),
                source_kind=str(rec0.get("source_kind", "capture_jsonl")),
                semantic_hint=str(rec0.get("semantic_hint", "")),
                phi_hint=(
                    _wrap_phase(_safe_float(rec0.get("phi_hint"), 0.0))
                    if rec0.get("phi_hint") is not None
                    else None
                ),
                harmonics_hint=_parse_harmonics(rec0.get("harmonics_hint")),
                stability_mean=_safe_float(rec0.get("stability_mean"), 0.0),
                drift=_safe_float(rec0.get("drift"), 0.0),
                voltage_mean=_safe_float(rec0.get("voltage_mean"), 0.0),
                pickup_mean=_safe_float(rec0.get("pickup_mean"), 0.0),
                pickup_std=_safe_float(rec0.get("pickup_std"), 0.0),
                aux_adc_1_mean=_safe_float(rec0.get("aux_adc_1_mean"), 0.0),
                aux_adc_2_mean=_safe_float(rec0.get("aux_adc_2_mean"), 0.0),
                magnetometer_x_mean=_safe_float(rec0.get("magnetometer_x_mean"), 0.0),
                magnetometer_y_mean=_safe_float(rec0.get("magnetometer_y_mean"), 0.0),
                magnetometer_z_mean=_safe_float(rec0.get("magnetometer_z_mean"), 0.0),
                ticks=_safe_int(rec0.get("ticks"), 0),
                locked=_safe_bool(rec0.get("locked"), False),
                metadata=(
                    dict(rec0.get("metadata", {}))
                    if isinstance(rec0.get("metadata"), dict)
                    else {"path": str(path)}
                ),
            )

    pickup_vals: List[float] = []
    aux1_vals: List[float] = []
    aux2_vals: List[float] = []
    mx_vals: List[float] = []
    my_vals: List[float] = []
    mz_vals: List[float] = []
    voltage_vals: List[float] = []
    stability_vals: List[float] = []
    phase_vals: List[float] = []

    expr_name = ""
    semantic_hint = ""
    phi_hint: Optional[float] = None
    harmonics_hint: List[int] = [1]
    ticks = 0
    locked = False

    for rec in records:
        ticks += 1

        expr = rec.get("expression", {})
        profile = rec.get("profile", {})
        internal = rec.get("internal_feedback", {})
        external = rec.get("external_sensors", {})

        if not expr_name:
            expr_name = str(expr.get("name", path.name))

        if phi_hint is None:
            if "phi" in expr:
                phi_hint = _safe_float(expr.get("phi"), 0.0)
            elif "phi" in profile:
                phi_hint = _safe_float(profile.get("phi"), 0.0)

        if not semantic_hint:
            semantic_hint = str(
                profile.get("metadata", {}).get(
                    "semantic_phi_state",
                    expr.get("metadata", {}).get("semantic_state", ""),
                )
            )

        if harmonics_hint == [1]:
            if "harmonics" in expr:
                harmonics_hint = _parse_harmonics(expr.get("harmonics"))
            elif "harmonics" in profile:
                harmonics_hint = _parse_harmonics(profile.get("harmonics"))

        measured_voltage = _safe_float(
            internal.get("measured_voltage", internal.get("voltage_mean")),
            0.0,
        )
        stability_score = _safe_float(
            internal.get("stability_score", internal.get("stability_mean")),
            0.0,
        )
        measured_phase = _safe_float(
            internal.get("measured_phase", internal.get("phase")),
            0.0,
        )

        pickup_voltage = _safe_float(
            external.get("pickup_voltage", external.get("pickup_mean")),
            0.0,
        )
        aux_adc_1 = _safe_float(
            external.get("aux_adc_1", external.get("aux_adc_1_mean")),
            0.0,
        )
        aux_adc_2 = _safe_float(
            external.get("aux_adc_2", external.get("aux_adc_2_mean")),
            0.0,
        )
        magnetometer_x = _safe_float(
            external.get("magnetometer_x", external.get("magnetometer_x_mean")),
            0.0,
        )
        magnetometer_y = _safe_float(
            external.get("magnetometer_y", external.get("magnetometer_y_mean")),
            0.0,
        )
        magnetometer_z = _safe_float(
            external.get("magnetometer_z", external.get("magnetometer_z_mean")),
            0.0,
        )

        voltage_vals.append(measured_voltage)
        stability_vals.append(stability_score)
        phase_vals.append(_wrap_phase(measured_phase))

        pickup_vals.append(pickup_voltage)
        aux1_vals.append(aux_adc_1)
        aux2_vals.append(aux_adc_2)
        mx_vals.append(magnetometer_x)
        my_vals.append(magnetometer_y)
        mz_vals.append(magnetometer_z)

        locked = locked or _safe_bool(rec.get("locked"), False)

    if phi_hint is None:
        phi_hint = _circular_phase_mean(phase_vals) if phase_vals else None

    return ObservationVector(
        source_name=path.name,
        source_kind="capture_jsonl",
        semantic_hint=semantic_hint or "",
        phi_hint=_wrap_phase(phi_hint) if phi_hint is not None else None,
        harmonics_hint=harmonics_hint,
        stability_mean=_mean(stability_vals),
        drift=_circular_phase_std(phase_vals),
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
            "expression_name": expr_name or path.stem,
            "path": str(path),
            "phase_mean_circular": _circular_phase_mean(phase_vals) if phase_vals else 0.0,
            "phase_sample_count": len(phase_vals),
        },
    )


# ---------------------------------------------------------------------
# Observation loading from response analysis JSON
# ---------------------------------------------------------------------
def _extract_analysis_observations(path: Path) -> List[ObservationVector]:
    if not path.exists():
        raise FileNotFoundError(f"Analysis file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict):
        if isinstance(payload.get("states"), list):
            rows = payload["states"]
        elif isinstance(payload.get("summary"), list):
            rows = payload["summary"]
        elif isinstance(payload.get("results"), list):
            rows = payload["results"]
        else:
            rows = []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    out: List[ObservationVector] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue

        phi_hint = (
            _safe_float(row.get("phi"), 0.0)
            if row.get("phi") is not None
            else None
        )

        out.append(
            ObservationVector(
                source_name=str(row.get("label", row.get("name", f"{path.name}#{idx}"))),
                source_kind="analysis_json",
                semantic_hint=str(row.get("semantic_state", row.get("state", ""))),
                phi_hint=_wrap_phase(phi_hint) if phi_hint is not None else None,
                harmonics_hint=_parse_harmonics(row.get("harmonics")),
                stability_mean=_safe_float(
                    row.get("stability", row.get("stability_mean", 0.0)),
                    0.0,
                ),
                drift=_safe_float(row.get("drift"), 0.0),
                voltage_mean=_safe_float(
                    row.get("voltage_mean", row.get("pickup_voltage_mean", 0.0)),
                    0.0,
                ),
                pickup_mean=_safe_float(
                    row.get("pickup_mean", row.get("pickup_voltage_mean", 0.0)),
                    0.0,
                ),
                pickup_std=_safe_float(
                    row.get("pickup_std", row.get("pickup_voltage_std", 0.0)),
                    0.0,
                ),
                aux_adc_1_mean=_safe_float(row.get("aux_adc_1_mean"), 0.0),
                aux_adc_2_mean=_safe_float(row.get("aux_adc_2_mean"), 0.0),
                magnetometer_x_mean=_safe_float(row.get("magnetometer_x_mean"), 0.0),
                magnetometer_y_mean=_safe_float(row.get("magnetometer_y_mean"), 0.0),
                magnetometer_z_mean=_safe_float(row.get("magnetometer_z_mean"), 0.0),
                ticks=_safe_int(row.get("ticks"), 0),
                locked=_safe_bool(row.get("locked"), False),
                metadata={"path": str(path)},
            )
        )

    return out


# ---------------------------------------------------------------------
# Manual observation
# ---------------------------------------------------------------------
def _manual_observation_from_args(args: argparse.Namespace) -> Optional[ObservationVector]:
    manual_fields = [
        args.pickup_mean,
        args.pickup_std,
        args.voltage_mean,
        args.stability_mean,
        args.drift,
        args.aux_adc_1_mean,
        args.aux_adc_2_mean,
        args.magnetometer_x_mean,
        args.magnetometer_y_mean,
        args.magnetometer_z_mean,
    ]

    if all(v is None for v in manual_fields):
        return None

    return ObservationVector(
        source_name="manual_observation",
        source_kind="manual",
        semantic_hint=args.semantic_hint or "",
        phi_hint=_wrap_phase(args.phi_hint) if args.phi_hint is not None else None,
        harmonics_hint=_parse_harmonics(args.harmonics_hint),
        stability_mean=_safe_float(args.stability_mean, 0.0),
        drift=_safe_float(args.drift, 0.0),
        voltage_mean=_safe_float(args.voltage_mean, 0.0),
        pickup_mean=_safe_float(args.pickup_mean, 0.0),
        pickup_std=_safe_float(args.pickup_std, 0.0),
        aux_adc_1_mean=_safe_float(args.aux_adc_1_mean, 0.0),
        aux_adc_2_mean=_safe_float(args.aux_adc_2_mean, 0.0),
        magnetometer_x_mean=_safe_float(args.magnetometer_x_mean, 0.0),
        magnetometer_y_mean=_safe_float(args.magnetometer_y_mean, 0.0),
        magnetometer_z_mean=_safe_float(args.magnetometer_z_mean, 0.0),
        ticks=_safe_int(args.ticks_hint, 0),
        locked=_safe_bool(args.locked_hint, False),
        metadata={},
    )


# ---------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------
def match_observation_to_catalog(
    obs: ObservationVector,
    catalog: List[CatalogSymbol],
    top_k: int = 5,
    weights: Optional[Dict[str, float]] = None,
) -> List[SymbolMatch]:
    matches: List[SymbolMatch] = []

    active_weights = weights or _default_decoder_weights()

    W_PICKUP = active_weights["W_PICKUP"]
    W_VOLTAGE = active_weights["W_VOLTAGE"]
    W_STABILITY = active_weights["W_STABILITY"]
    W_DRIFT = active_weights["W_DRIFT"]
    W_PHI = active_weights["W_PHI"]
    W_AUX1 = active_weights["W_AUX1"]
    W_AUX2 = active_weights["W_AUX2"]
    W_MX = active_weights["W_MX"]
    W_MY = active_weights["W_MY"]
    W_MZ = active_weights["W_MZ"]
    W_HARM = active_weights["W_HARM"]

    for sym in catalog:
        pickup_scale = max(sym.pickup_std, sym.pickup_capture_std, 0.02)
        voltage_scale = max(sym.voltage_std, 0.01)
        stability_scale = max(sym.stability_std, 0.01)
        drift_scale = max(sym.drift_std, 0.003)

        pickup_delta = _norm_delta(
            obs.pickup_mean,
            sym.mean_pickup,
            pickup_scale,
            floor=0.02,
            cap=6.0,
        )
        voltage_delta = _norm_delta(
            obs.voltage_mean,
            sym.voltage_mean,
            voltage_scale,
            floor=0.01,
            cap=4.0,
        )
        stability_delta = _norm_delta(
            obs.stability_mean,
            sym.stability,
            stability_scale,
            floor=0.01,
            cap=4.0,
        )
        drift_delta = _norm_delta(
            obs.drift,
            sym.drift,
            drift_scale,
            floor=0.003,
            cap=4.0,
        )

        phi_delta = 0.0
        if obs.phi_hint is not None:
            phi_delta = _phase_distance(obs.phi_hint, sym.phi) / math.pi

        aux_adc_1_delta = _norm_delta(
            obs.aux_adc_1_mean,
            sym.aux_adc_1_mean,
            max(sym.aux_adc_1_std, 0.01),
            floor=0.01,
            cap=4.0,
        )
        aux_adc_2_delta = _norm_delta(
            obs.aux_adc_2_mean,
            sym.aux_adc_2_mean,
            max(sym.aux_adc_2_std, 0.01),
            floor=0.01,
            cap=4.0,
        )
        magnetometer_x_delta = _norm_delta(
            obs.magnetometer_x_mean,
            sym.magnetometer_x_mean,
            max(sym.magnetometer_x_std, 0.01),
            floor=0.01,
            cap=4.0,
        )
        magnetometer_y_delta = _norm_delta(
            obs.magnetometer_y_mean,
            sym.magnetometer_y_mean,
            max(sym.magnetometer_y_std, 0.01),
            floor=0.01,
            cap=4.0,
        )
        magnetometer_z_delta = _norm_delta(
            obs.magnetometer_z_mean,
            sym.magnetometer_z_mean,
            max(sym.magnetometer_z_std, 0.01),
            floor=0.01,
            cap=4.0,
        )
        harmonics_distance = _harmonics_distance(obs.harmonics_hint, sym.harmonics)

        semantic_bonus = 0.0
        if obs.semantic_hint and obs.semantic_hint == sym.semantic_state:
            semantic_bonus = 0.10

        raw_distance = (
            (pickup_delta * W_PICKUP)
            + (voltage_delta * W_VOLTAGE)
            + (stability_delta * W_STABILITY)
            + (drift_delta * W_DRIFT)
            + (phi_delta * W_PHI)
            + (aux_adc_1_delta * W_AUX1)
            + (aux_adc_2_delta * W_AUX2)
            + (magnetometer_x_delta * W_MX)
            + (magnetometer_y_delta * W_MY)
            + (magnetometer_z_delta * W_MZ)
            + (harmonics_distance * W_HARM)
        )

        distance_total = raw_distance * (0.90 if semantic_bonus > 0.0 else 1.0)

        confidence = _clamp(math.exp(-distance_total), 0.0, 1.0)

        matches.append(
            SymbolMatch(
                symbol_id=sym.symbol_id,
                name=sym.name,
                semantic_state=sym.semantic_state,
                distance_total=distance_total,
                confidence=confidence,
                pickup_delta=pickup_delta,
                voltage_delta=voltage_delta,
                stability_delta=stability_delta,
                drift_delta=drift_delta,
                phi_delta=phi_delta,
                aux_adc_1_delta=aux_adc_1_delta,
                aux_adc_2_delta=aux_adc_2_delta,
                magnetometer_x_delta=magnetometer_x_delta,
                magnetometer_y_delta=magnetometer_y_delta,
                magnetometer_z_delta=magnetometer_z_delta,
                harmonics_distance=harmonics_distance,
                semantic_bonus=semantic_bonus,
                rank_score=sym.rank_score,
            )
        )

    matches.sort(key=lambda m: (m.distance_total, -m.rank_score, -m.confidence))
    return matches[:max(1, top_k)]

def build_decode_result(obs: ObservationVector, matches: List[SymbolMatch]) -> DecodeResult:
    best = matches[0]
    runner_up = matches[1] if len(matches) > 1 else None
    margin = (
        (runner_up.distance_total - best.distance_total)
        if runner_up is not None
        else best.distance_total
    )

    return DecodeResult(
        source_name=obs.source_name,
        source_kind=obs.source_kind,
        semantic_hint=obs.semantic_hint,
        predicted_symbol_id=best.symbol_id,
        predicted_name=best.name,
        predicted_semantic_state=best.semantic_state,
        confidence=best.confidence,
        runner_up_symbol_id=runner_up.symbol_id if runner_up else "",
        runner_up_name=runner_up.name if runner_up else "",
        margin=margin,
        observation=asdict(obs),
        top_matches=[asdict(m) for m in matches],
    )


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------
def write_report_json(path: Path, catalog_path: Path, results: List[DecodeResult]) -> None:
    payload = {
        "catalog": str(catalog_path),
        "result_count": len(results),
        "results": [asdict(r) for r in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_report_csv(path: Path, results: List[DecodeResult]) -> None:
    fieldnames = [
        "source_name",
        "source_kind",
        "semantic_hint",
        "predicted_symbol_id",
        "predicted_name",
        "predicted_semantic_state",
        "confidence",
        "runner_up_symbol_id",
        "runner_up_name",
        "margin",
        "pickup_mean",
        "pickup_std",
        "voltage_mean",
        "stability_mean",
        "drift",
        "harmonics_hint",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            obs = res.observation
            writer.writerow(
                {
                    "source_name": res.source_name,
                    "source_kind": res.source_kind,
                    "semantic_hint": res.semantic_hint,
                    "predicted_symbol_id": res.predicted_symbol_id,
                    "predicted_name": res.predicted_name,
                    "predicted_semantic_state": res.predicted_semantic_state,
                    "confidence": f"{res.confidence:.6f}",
                    "runner_up_symbol_id": res.runner_up_symbol_id,
                    "runner_up_name": res.runner_up_name,
                    "margin": f"{res.margin:.6f}",
                    "pickup_mean": f"{_safe_float(obs.get('pickup_mean'), 0.0):.6f}",
                    "pickup_std": f"{_safe_float(obs.get('pickup_std'), 0.0):.6f}",
                    "voltage_mean": f"{_safe_float(obs.get('voltage_mean'), 0.0):.6f}",
                    "stability_mean": f"{_safe_float(obs.get('stability_mean'), 0.0):.6f}",
                    "drift": f"{_safe_float(obs.get('drift'), 0.0):.6f}",
                    "harmonics_hint": json.dumps(obs.get("harmonics_hint", [1])),
                }
            )


# ---------------------------------------------------------------------
# OO wrapper for validation/runtime imports
# ---------------------------------------------------------------------
class SymaticsSymbolDecoder:
    """
    Thin OO wrapper around the functional decoder pipeline.

    Exists so validation / future runtime code can import a stable class API.
    """

    def __init__(
        self,
        catalog_path: str | Path,
        calibration_path: str | Path | None = None,
    ):
        self.catalog_path = Path(catalog_path)
        self.calibration_path = Path(calibration_path) if calibration_path else None
        self.catalog = load_catalog(self.catalog_path)
        self.weights = _load_calibrated_decoder_weights(self.calibration_path)

    def decode_observation(
        self,
        observation: ObservationVector,
        top_k: int = 5,
    ) -> DecodeResult:
        matches = match_observation_to_catalog(
            observation,
            self.catalog,
            top_k=top_k,
            weights=self.weights,
        )
        return build_decode_result(observation, matches)

    def decode_capture(
        self,
        capture_path: str | Path,
        top_k: int = 5,
    ) -> DecodeResult:
        obs = _extract_capture_observation(Path(capture_path))
        return self.decode_observation(obs, top_k=top_k)

    def decode_analysis_json(
        self,
        analysis_path: str | Path,
        top_k: int = 5,
    ) -> List[DecodeResult]:
        observations = _extract_analysis_observations(Path(analysis_path))
        return [self.decode_observation(obs, top_k=top_k) for obs in observations]

    def decode_manual(
        self,
        *,
        semantic_hint: str = "",
        phi_hint: float | None = None,
        harmonics_hint: Any = None,
        pickup_mean: float = 0.0,
        pickup_std: float = 0.0,
        voltage_mean: float = 0.0,
        stability_mean: float = 0.0,
        drift: float = 0.0,
        aux_adc_1_mean: float = 0.0,
        aux_adc_2_mean: float = 0.0,
        magnetometer_x_mean: float = 0.0,
        magnetometer_y_mean: float = 0.0,
        magnetometer_z_mean: float = 0.0,
        ticks: int = 0,
        locked: bool = False,
        source_name: str = "manual_observation",
        top_k: int = 5,
    ) -> DecodeResult:
        obs = ObservationVector(
            source_name=source_name,
            source_kind="manual",
            semantic_hint=semantic_hint,
            phi_hint=_wrap_phase(phi_hint) if phi_hint is not None else None,
            harmonics_hint=_parse_harmonics(harmonics_hint),
            stability_mean=float(stability_mean),
            drift=float(drift),
            voltage_mean=float(voltage_mean),
            pickup_mean=float(pickup_mean),
            pickup_std=float(pickup_std),
            aux_adc_1_mean=float(aux_adc_1_mean),
            aux_adc_2_mean=float(aux_adc_2_mean),
            magnetometer_x_mean=float(magnetometer_x_mean),
            magnetometer_y_mean=float(magnetometer_y_mean),
            magnetometer_z_mean=float(magnetometer_z_mean),
            ticks=int(ticks),
            locked=bool(locked),
            metadata={},
        )
        return self.decode_observation(obs, top_k=top_k)


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decode measured Symatics responses against a symbol catalog"
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG_PATH),
        help="Path to symatics_symbol_catalog.json",
    )
    parser.add_argument(
        "--capture",
        nargs="*",
        default=[],
        help="One or more symatics_capture JSONL files",
    )
    parser.add_argument(
        "--analysis-json",
        nargs="*",
        default=[],
        help="Optional symatics_response_analysis JSON files",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of top matches to keep per observation",
    )
    parser.add_argument(
        "--json-out",
        default=str(DEFAULT_JSON_OUT),
        help="Output JSON report path",
    )
    parser.add_argument(
        "--csv-out",
        default=str(DEFAULT_CSV_OUT),
        help="Output CSV report path",
    )
    parser.add_argument(
        "--calibration",
        default=None,
        help="Optional decoder calibration JSON path",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write JSON/CSV reports",
    )

    parser.add_argument("--semantic-hint", default="", help="Optional semantic hint")
    parser.add_argument("--phi-hint", type=float, default=None, help="Optional phase hint")
    parser.add_argument(
        "--harmonics-hint",
        nargs="*",
        default=None,
        help='Optional harmonics hint, e.g. --harmonics-hint 1 2 or --harmonics-hint "1,2"',
    )
    parser.add_argument("--pickup-mean", type=float, default=None)
    parser.add_argument("--pickup-std", type=float, default=None)
    parser.add_argument("--voltage-mean", type=float, default=None)
    parser.add_argument("--stability-mean", type=float, default=None)
    parser.add_argument("--drift", type=float, default=None)
    parser.add_argument("--aux-adc-1-mean", type=float, default=None)
    parser.add_argument("--aux-adc-2-mean", type=float, default=None)
    parser.add_argument("--magnetometer-x-mean", type=float, default=None)
    parser.add_argument("--magnetometer-y-mean", type=float, default=None)
    parser.add_argument("--magnetometer-z-mean", type=float, default=None)
    parser.add_argument("--ticks-hint", type=int, default=0)
    parser.add_argument("--locked-hint", action="store_true")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    catalog_path = Path(args.catalog)
    json_out = Path(getattr(args, "json_out", DEFAULT_JSON_OUT))
    csv_out = Path(getattr(args, "csv_out", DEFAULT_CSV_OUT))

    calibration_raw = getattr(args, "calibration", None)
    calibration_path = Path(calibration_raw) if calibration_raw else None

    decoder = SymaticsSymbolDecoder(
        catalog_path,
        calibration_path=calibration_path,
    )

    observations: List[ObservationVector] = []

    for capture_path in getattr(args, "capture", []):
        observations.append(_extract_capture_observation(Path(capture_path)))

    for analysis_path in getattr(args, "analysis_json", []):
        observations.extend(_extract_analysis_observations(Path(analysis_path)))

    manual_obs = _manual_observation_from_args(args)
    if manual_obs is not None:
        observations.append(manual_obs)

    if not observations:
        raise SystemExit(
            "No observations supplied. Use --capture, --analysis-json, or manual feature arguments."
        )

    results: List[DecodeResult] = []
    for obs in observations:
        results.append(decoder.decode_observation(obs, top_k=args.top_k))

    print("=== Symatics Symbol Decoder ===")
    print(f"Catalog     : {catalog_path}")
    print(f"Catalog size: {len(decoder.catalog)}")
    print(f"Observations: {len(observations)}")
    if calibration_path is not None:
        print(f"Calibration : {calibration_path}")
    else:
        print("Calibration : <defaults only>")
    print()

    print("Active decoder weights:")
    for key, value in decoder.weights.items():
        print(f"  {key}={value:.6f}")
    print()

    for res in results:
        print(f"Source      : {res.source_name}")
        print(f"Kind        : {res.source_kind}")
        print(f"Predicted   : {res.predicted_symbol_id} | {res.predicted_name}")
        print(f"Semantic    : {res.predicted_semantic_state}")
        print(f"Confidence  : {res.confidence:.6f}")
        if res.runner_up_symbol_id:
            print(
                f"Runner-up   : {res.runner_up_symbol_id} | {res.runner_up_name} "
                f"| margin={res.margin:.6f}"
            )
        print("Top matches :")
        for match in res.top_matches:
            print(
                "  - "
                f"{match['symbol_id']} | {match['semantic_state']} | "
                f"distance={match['distance_total']:.6f} | "
                f"confidence={match['confidence']:.6f} | "
                f"pickupΔ={match['pickup_delta']:.6f} | "
                f"stabilityΔ={match['stability_delta']:.6f} | "
                f"driftΔ={match['drift_delta']:.6f} | "
                f"phiΔ={match['phi_delta']:.6f}"
            )
        print()

    if not args.no_write:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        write_report_json(json_out, catalog_path, results)
        write_report_csv(csv_out, results)
        print(f"JSON: {json_out}")
        print(f"CSV : {csv_out}")


if __name__ == "__main__":
    main()