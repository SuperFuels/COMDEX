from __future__ import annotations

"""
Symatics Symbol Decoder Calibration
-----------------------------------
Calibrate decoder feature weights from repeated trial/reference data.

Purpose
- read the production reference catalog
- read repeated write/read trial results
- estimate which features separate symbols most strongly
- produce calibrated decoder weights for operational decoding

Inputs
- symatics_symbol_reference_catalog.json
- symatics_symbol_write_read_trials_report.json

Outputs
- symatics_symbol_decoder_calibration.json

Why this exists
---------------
The discovery decoder used hand-tuned weights. That was enough to prove the loop.
Now that repeated trials are stable, we can derive a more defensible operational
weight profile from measured symbol separation.

This does NOT replace the catalog.
It produces a calibration artifact the decoder can optionally load.

Typical usage
-------------
    PYTHONPATH=. python backend/modules/dimensions/ucs/zones/experiments/qwave_engine/symatics_symbol_decoder_calibration.py \
      --reference-catalog backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_reference_catalog.json \
      --trials-report backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/symatics_symbol_write_read_trials_report.json
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

DEFAULT_REFERENCE_CATALOG = OUTPUT_DIR / "symatics_symbol_reference_catalog.json"
DEFAULT_TRIALS_REPORT = OUTPUT_DIR / "symatics_symbol_write_read_trials_report.json"
DEFAULT_CALIBRATION_OUT = OUTPUT_DIR / "symatics_symbol_decoder_calibration.json"

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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _phase_distance(a: float, b: float) -> float:
    a = _wrap_phase(a)
    b = _wrap_phase(b)
    d = abs(a - b)
    return min(d, TWO_PI - d)


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


def _harmonics_distance(a: List[int], b: List[int]) -> float:
    sa = set(int(x) for x in a)
    sb = set(int(x) for x in b)
    union = sa | sb
    if not union:
        return 0.0
    inter = sa & sb
    return 1.0 - (len(inter) / len(union))


# ---------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------
def load_reference_catalog(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Reference catalog not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("symbols"), list):
        rows = payload["symbols"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError(f"Unrecognized reference catalog format: {path}")

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("symbol_id", "")).strip()
        if not sid:
            continue
        out[sid] = row

    if not out:
        raise ValueError(f"No symbols loaded from reference catalog: {path}")

    return out


def load_trials_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Trials report not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Trials report must be a JSON object: {path}")
    return payload


# ---------------------------------------------------------------------
# Separation analysis
# ---------------------------------------------------------------------
def _reference_feature_vector(symbol: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "phi": _safe_float(symbol.get("phi"), 0.0),
        "harmonics": _parse_harmonics(symbol.get("harmonics")),
        "pickup_mean": _safe_float(symbol.get("pickup_mean"), 0.0),
        "pickup_std": max(_safe_float(symbol.get("pickup_std"), 0.0), 1e-6),
        "stability_mean": _safe_float(
            symbol.get("stability_mean", symbol.get("stability", 0.0)),
            0.0,
        ),
        "stability_std": max(_safe_float(symbol.get("stability_std"), 0.0), 1e-6),
        "drift_mean": _safe_float(symbol.get("drift_mean", symbol.get("drift", 0.0)), 0.0),
        "drift_std": max(_safe_float(symbol.get("drift_std"), 0.0), 1e-6),
        "voltage_mean": _safe_float(symbol.get("voltage_mean"), 0.0),
        "voltage_std": max(_safe_float(symbol.get("voltage_std"), 0.0), 1e-6),
        "aux_adc_1_mean": _safe_float(symbol.get("aux_adc_1_mean"), 0.0),
        "aux_adc_1_std": max(_safe_float(symbol.get("aux_adc_1_std"), 0.0), 1e-6),
        "aux_adc_2_mean": _safe_float(symbol.get("aux_adc_2_mean"), 0.0),
        "aux_adc_2_std": max(_safe_float(symbol.get("aux_adc_2_std"), 0.0), 1e-6),
        "magnetometer_x_mean": _safe_float(symbol.get("magnetometer_x_mean"), 0.0),
        "magnetometer_x_std": max(_safe_float(symbol.get("magnetometer_x_std"), 0.0), 1e-6),
        "magnetometer_y_mean": _safe_float(symbol.get("magnetometer_y_mean"), 0.0),
        "magnetometer_y_std": max(_safe_float(symbol.get("magnetometer_y_std"), 0.0), 1e-6),
        "magnetometer_z_mean": _safe_float(symbol.get("magnetometer_z_mean"), 0.0),
        "magnetometer_z_std": max(_safe_float(symbol.get("magnetometer_z_std"), 0.0), 1e-6),
    }


def _pairwise_separation(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, float]:
    def sep(mean_a: float, std_a: float, mean_b: float, std_b: float) -> float:
        pooled = max(math.sqrt((std_a ** 2 + std_b ** 2) / 2.0), 1e-6)
        return abs(mean_a - mean_b) / pooled

    return {
        "pickup": sep(a["pickup_mean"], a["pickup_std"], b["pickup_mean"], b["pickup_std"]),
        "stability": sep(
            a["stability_mean"], a["stability_std"], b["stability_mean"], b["stability_std"]
        ),
        "drift": sep(a["drift_mean"], a["drift_std"], b["drift_mean"], b["drift_std"]),
        "voltage": sep(a["voltage_mean"], a["voltage_std"], b["voltage_mean"], b["voltage_std"]),
        "aux_adc_1": sep(
            a["aux_adc_1_mean"], a["aux_adc_1_std"], b["aux_adc_1_mean"], b["aux_adc_1_std"]
        ),
        "aux_adc_2": sep(
            a["aux_adc_2_mean"], a["aux_adc_2_std"], b["aux_adc_2_mean"], b["aux_adc_2_std"]
        ),
        "magnetometer_x": sep(
            a["magnetometer_x_mean"],
            a["magnetometer_x_std"],
            b["magnetometer_x_mean"],
            b["magnetometer_x_std"],
        ),
        "magnetometer_y": sep(
            a["magnetometer_y_mean"],
            a["magnetometer_y_std"],
            b["magnetometer_y_mean"],
            b["magnetometer_y_std"],
        ),
        "magnetometer_z": sep(
            a["magnetometer_z_mean"],
            a["magnetometer_z_std"],
            b["magnetometer_z_mean"],
            b["magnetometer_z_std"],
        ),
        "phi": _phase_distance(a["phi"], b["phi"]) / math.pi,
        "harmonics": _harmonics_distance(a["harmonics"], b["harmonics"]),
    }


def derive_feature_weights(reference_catalog: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    symbols = list(reference_catalog.keys())
    if len(symbols) < 2:
        raise ValueError("Need at least two symbols to derive calibration weights")

    pair_scores: Dict[str, List[float]] = {
        "pickup": [],
        "stability": [],
        "drift": [],
        "voltage": [],
        "aux_adc_1": [],
        "aux_adc_2": [],
        "magnetometer_x": [],
        "magnetometer_y": [],
        "magnetometer_z": [],
        "phi": [],
        "harmonics": [],
    }

    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            a = _reference_feature_vector(reference_catalog[symbols[i]])
            b = _reference_feature_vector(reference_catalog[symbols[j]])
            scores = _pairwise_separation(a, b)
            for key, val in scores.items():
                pair_scores[key].append(val)

    mean_scores = {
        key: (sum(vals) / len(vals) if vals else 0.0)
        for key, vals in pair_scores.items()
    }

    # Drift should not dominate just because it is numerically tiny.
    # Pickup/stability remain primary. Phi/harmonics are structural priors.
    raw = {
        "pickup": mean_scores["pickup"] * 1.35,
        "stability": mean_scores["stability"] * 1.10,
        "drift": mean_scores["drift"] * 0.60,
        "voltage": mean_scores["voltage"] * 0.85,
        "phi": max(mean_scores["phi"], 0.25) * 0.90,
        "harmonics": max(mean_scores["harmonics"], 0.25) * 0.80,
        "aux_adc_1": mean_scores["aux_adc_1"] * 0.55,
        "aux_adc_2": mean_scores["aux_adc_2"] * 0.55,
        "magnetometer_x": mean_scores["magnetometer_x"] * 0.40,
        "magnetometer_y": mean_scores["magnetometer_y"] * 0.40,
        "magnetometer_z": mean_scores["magnetometer_z"] * 0.40,
    }

    total = sum(max(v, 1e-6) for v in raw.values())
    normalized = {key: (max(val, 1e-6) / total) for key, val in raw.items()}

    # Scale into a practical decoder range similar to your current hand-tuned values.
    scaled = {
        "W_PICKUP": round(normalized["pickup"] * 10.0, 6),
        "W_STABILITY": round(normalized["stability"] * 10.0, 6),
        "W_DRIFT": round(normalized["drift"] * 10.0, 6),
        "W_VOLTAGE": round(normalized["voltage"] * 10.0, 6),
        "W_PHI": round(normalized["phi"] * 10.0, 6),
        "W_HARM": round(normalized["harmonics"] * 10.0, 6),
        "W_AUX1": round(normalized["aux_adc_1"] * 10.0, 6),
        "W_AUX2": round(normalized["aux_adc_2"] * 10.0, 6),
        "W_MX": round(normalized["magnetometer_x"] * 10.0, 6),
        "W_MY": round(normalized["magnetometer_y"] * 10.0, 6),
        "W_MZ": round(normalized["magnetometer_z"] * 10.0, 6),
    }

    return scaled


# ---------------------------------------------------------------------
# Trials-derived confidence context
# ---------------------------------------------------------------------
def derive_runtime_hints(trials_report: Dict[str, Any]) -> Dict[str, Any]:
    summaries = trials_report.get("per_symbol_summary", [])
    if not isinstance(summaries, list):
        summaries = []

    mean_confidences = []
    mean_margins = []

    for row in summaries:
        if not isinstance(row, dict):
            continue
        mean_confidences.append(_safe_float(row.get("mean_confidence"), 0.0))
        mean_margins.append(_safe_float(row.get("mean_margin"), 0.0))

    return {
        "expected_mean_confidence": round(
            sum(mean_confidences) / len(mean_confidences), 6
        ) if mean_confidences else 0.0,
        "expected_mean_margin": round(
            sum(mean_margins) / len(mean_margins), 6
        ) if mean_margins else 0.0,
        "trial_exact_accuracy": _safe_float(
            trials_report.get("overall_metrics", {}).get("exact_accuracy"),
            0.0,
        ),
        "trial_semantic_accuracy": _safe_float(
            trials_report.get("overall_metrics", {}).get("semantic_accuracy"),
            0.0,
        ),
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibrate Symatics decoder weights from reference and trial data"
    )
    parser.add_argument(
        "--reference-catalog",
        default=str(DEFAULT_REFERENCE_CATALOG),
        help="Path to symatics_symbol_reference_catalog.json",
    )
    parser.add_argument(
        "--trials-report",
        default=str(DEFAULT_TRIALS_REPORT),
        help="Path to symatics_symbol_write_read_trials_report.json",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_CALIBRATION_OUT),
        help="Output calibration JSON path",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    reference_catalog_path = Path(args.reference_catalog)
    trials_report_path = Path(args.trials_report)
    out_path = Path(args.out)

    reference_catalog = load_reference_catalog(reference_catalog_path)
    trials_report = load_trials_report(trials_report_path)

    weights = derive_feature_weights(reference_catalog)
    runtime_hints = derive_runtime_hints(trials_report)

    payload = {
        "reference_catalog": str(reference_catalog_path),
        "trials_report": str(trials_report_path),
        "symbol_ids": sorted(reference_catalog.keys()),
        "decoder_weights": weights,
        "runtime_hints": runtime_hints,
        "notes": {
            "profile": "operational_decoder_calibration_v1",
            "basis": "reference_catalog_plus_repeated_trials",
            "comment": (
                "Derived after stable Tier-1 repeated trials. "
                "Use with reference catalog for operational decoding."
            ),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("=== Symatics Symbol Decoder Calibration ===")
    print(f"Reference catalog : {reference_catalog_path}")
    print(f"Trials report     : {trials_report_path}")
    print(f"Symbols           : {sorted(reference_catalog.keys())}")
    print()
    for key, val in weights.items():
        print(f"{key:12s}: {val:.6f}")
    print()
    print(
        "Runtime hints    : "
        f"mean_conf={runtime_hints['expected_mean_confidence']:.6f} | "
        f"mean_margin={runtime_hints['expected_mean_margin']:.6f} | "
        f"exact_acc={runtime_hints['trial_exact_accuracy']:.6f}"
    )
    print()
    print(f"JSON             : {out_path}")


if __name__ == "__main__":
    main()