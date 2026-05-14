from __future__ import annotations

"""
Symatics Symbol Validation
--------------------------
Validate write/read agreement for the Symatics symbol system.

Purpose
- Load a canonical symbol catalog
- Decode one or more capture JSONL files using the existing decoder
- Compare predicted symbols against expected symbols
- Produce:
    * per-capture validation rows
    * confusion matrix
    * per-symbol accuracy
    * overall agreement metrics

Inputs
- symatics_symbol_catalog.json
- one or more capture JSONL files from symatics_capture.py

Outputs
- symatics_symbol_validation_report.json
- symatics_symbol_validation_report.csv
- symatics_symbol_validation_confusion_matrix.csv

Notes
- This is replay-based validation first.
- It uses the decoder logic already established in symatics_symbol_decoder.py
  so validation and decoding stay aligned.
"""

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_symbol_decoder import (
    DecodeResult,
    SymaticsSymbolDecoder,
)

OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _phase_distance(a: float, b: float) -> float:
    a = _wrap_phase(a)
    b = _wrap_phase(b)
    d = abs(a - b)
    return min(d, TWO_PI - d)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


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
            parsed = json.loads(text)
            return _parse_harmonics(parsed)
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


def _normalize_name(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def _harmonics_key(harmonics: Iterable[int]) -> str:
    return ",".join(str(int(h)) for h in harmonics)


# ---------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------
@dataclass(slots=True)
class ValidationCase:
    source: str
    source_kind: str
    expected_symbol_id: Optional[str]
    expected_semantic_state: Optional[str]
    expected_phi: Optional[float]
    expected_harmonics: Optional[List[int]]
    predicted_symbol_id: Optional[str]
    predicted_name: Optional[str]
    predicted_semantic_state: Optional[str]
    predicted_phi: Optional[float]
    predicted_harmonics: Optional[List[int]]
    confidence: float
    distance: float
    runner_up_symbol_id: Optional[str]
    runner_up_confidence: float
    margin: float
    agreed_symbol: Optional[bool]
    agreed_semantic_state: Optional[bool]
    observation_pickup: float
    observation_stability: float
    observation_drift: float
    observation_phi: Optional[float]
    notes: Dict[str, Any]


@dataclass(slots=True)
class PerSymbolSummary:
    symbol_id: str
    semantic_state: str
    samples: int
    exact_symbol_hits: int
    semantic_hits: int
    exact_symbol_accuracy: float
    semantic_accuracy: float
    mean_confidence: float
    min_confidence: float
    max_confidence: float


# ---------------------------------------------------------------------
# Catalog utilities
# ---------------------------------------------------------------------
def load_catalog(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("symbols"), list):
        return payload
    if isinstance(payload, list):
        return {"symbols": payload}
    raise ValueError(f"Unrecognized catalog format: {path}")


def catalog_symbols_by_id(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for sym in payload.get("symbols", []):
        symbol_id = str(sym.get("symbol_id", "")).strip()
        if symbol_id:
            out[symbol_id] = sym
    return out


def nearest_catalog_symbol_by_phi_harmonics(
    catalog_payload: Dict[str, Any],
    phi: Optional[float],
    harmonics: Optional[List[int]],
) -> Optional[Dict[str, Any]]:
    if phi is None:
        return None

    harmonics = harmonics or []
    best: Optional[Dict[str, Any]] = None
    best_score = float("inf")

    for sym in catalog_payload.get("symbols", []):
        sym_phi = _safe_float(sym.get("phi"), default=0.0)
        sym_harm = _parse_harmonics(sym.get("harmonics"))
        phase_score = _phase_distance(phi, sym_phi)

        harm_penalty = 0.0
        if harmonics:
            harm_penalty = 0.0 if sym_harm == harmonics else 0.25

        score = phase_score + harm_penalty
        if score < best_score:
            best_score = score
            best = sym

    return best


# ---------------------------------------------------------------------
# Expected-label inference
# ---------------------------------------------------------------------
def parse_expected_mapping(items: List[str]) -> Dict[str, str]:
    """
    Accept entries like:
        file1.jsonl=S0
        another_capture.jsonl=S2
    Stores by basename and by full string key.
    """
    mapping: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            continue
        left, right = item.split("=", 1)
        key = left.strip()
        val = right.strip()
        if not key or not val:
            continue
        mapping[key] = val
        mapping[Path(key).name] = val
    return mapping


def infer_expected_from_filename(
    path: Path,
    catalog_payload: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    name = _normalize_name(path.stem)
    hits: List[Tuple[int, Dict[str, Any]]] = []

    for sym in catalog_payload.get("symbols", []):
        sid = _normalize_name(str(sym.get("symbol_id", "")))
        sname = _normalize_name(str(sym.get("name", "")))
        state = _normalize_name(str(sym.get("semantic_state", "")))

        score = 0
        if sid and sid in name:
            score += 5
        if sname and sname in name:
            score += 4
        if state and state in name:
            score += 2

        if score > 0:
            hits.append((score, sym))

    if not hits:
        return None

    hits.sort(key=lambda x: x[0], reverse=True)
    return hits[0][1]


def infer_expected_symbol(
    capture_path: Path,
    decoder_observation: Dict[str, Any],
    catalog_payload: Dict[str, Any],
    explicit_mapping: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    by_id = catalog_symbols_by_id(catalog_payload)

    mapped = explicit_mapping.get(str(capture_path)) or explicit_mapping.get(capture_path.name)
    if mapped and mapped in by_id:
        return by_id[mapped]

    phi = decoder_observation.get("phi_hint")
    harmonics = decoder_observation.get("harmonics_hint")
    if phi is not None:
        sym = nearest_catalog_symbol_by_phi_harmonics(
            catalog_payload=catalog_payload,
            phi=_safe_float(phi, default=0.0),
            harmonics=_parse_harmonics(harmonics),
        )
        if sym is not None:
            return sym

    return infer_expected_from_filename(capture_path, catalog_payload)


# ---------------------------------------------------------------------
# Validation core
# ---------------------------------------------------------------------
def build_validation_case(
    capture_path: Path,
    decode_result: DecodeResult,
    expected_symbol: Optional[Dict[str, Any]],
) -> ValidationCase:
    observation: Dict[str, Any] = dict(decode_result.observation or {})
    matches: List[Dict[str, Any]] = list(decode_result.top_matches or [])

    best = matches[0] if matches else {}
    runner_up = matches[1] if len(matches) > 1 else {}

    predicted_symbol_id = decode_result.predicted_symbol_id or None
    predicted_name = decode_result.predicted_name or None
    predicted_semantic_state = decode_result.predicted_semantic_state or None

    predicted_phi = best.get("phi")
    if predicted_phi is None and predicted_symbol_id:
        predicted_phi = None

    predicted_harmonics = (
        _parse_harmonics(best.get("harmonics"))
        if best.get("harmonics") is not None
        else None
    )

    confidence = _safe_float(decode_result.confidence, default=0.0)
    distance = _safe_float(best.get("distance_total", best.get("distance", 999.0)), default=999.0)

    runner_up_symbol_id = decode_result.runner_up_symbol_id or None
    runner_up_confidence = _safe_float(runner_up.get("confidence"), default=0.0)
    margin = _safe_float(decode_result.margin, default=0.0)

    expected_symbol_id = None
    expected_semantic_state = None
    expected_phi = None
    expected_harmonics = None

    if expected_symbol is not None:
        expected_symbol_id = str(expected_symbol.get("symbol_id", "")).strip() or None
        expected_semantic_state = str(expected_symbol.get("semantic_state", "")).strip() or None
        expected_phi = _safe_float(expected_symbol.get("phi"), default=0.0)
        expected_harmonics = _parse_harmonics(expected_symbol.get("harmonics"))

    agreed_symbol: Optional[bool] = None
    agreed_semantic_state: Optional[bool] = None
    if expected_symbol_id is not None and predicted_symbol_id is not None:
        agreed_symbol = expected_symbol_id == predicted_symbol_id
    if expected_semantic_state is not None and predicted_semantic_state is not None:
        agreed_semantic_state = expected_semantic_state == predicted_semantic_state

    observation_pickup = _safe_float(observation.get("pickup_mean"), default=0.0)
    observation_stability = _safe_float(observation.get("stability_mean"), default=0.0)
    observation_drift = _safe_float(observation.get("drift"), default=0.0)

    observation_phi = observation.get("phi_hint")
    if observation_phi is not None:
        observation_phi = _safe_float(observation_phi, default=0.0)

    return ValidationCase(
        source=str(capture_path),
        source_kind=decode_result.source_kind,
        expected_symbol_id=expected_symbol_id,
        expected_semantic_state=expected_semantic_state,
        expected_phi=expected_phi,
        expected_harmonics=expected_harmonics,
        predicted_symbol_id=predicted_symbol_id,
        predicted_name=predicted_name,
        predicted_semantic_state=predicted_semantic_state,
        predicted_phi=_safe_float(predicted_phi, default=0.0) if predicted_phi is not None else None,
        predicted_harmonics=predicted_harmonics,
        confidence=confidence,
        distance=distance,
        runner_up_symbol_id=runner_up_symbol_id,
        runner_up_confidence=runner_up_confidence,
        margin=margin,
        agreed_symbol=agreed_symbol,
        agreed_semantic_state=agreed_semantic_state,
        observation_pickup=observation_pickup,
        observation_stability=observation_stability,
        observation_drift=observation_drift,
        observation_phi=observation_phi,
        notes={
            "match_count": len(matches),
            "expected_harmonics_key": _harmonics_key(expected_harmonics or []),
            "predicted_harmonics_key": _harmonics_key(predicted_harmonics or []),
        },
    )


def per_symbol_summary(cases: List[ValidationCase]) -> List[PerSymbolSummary]:
    grouped: Dict[str, List[ValidationCase]] = defaultdict(list)

    for case in cases:
        if case.expected_symbol_id:
            grouped[case.expected_symbol_id].append(case)

    out: List[PerSymbolSummary] = []
    for symbol_id, items in grouped.items():
        semantic_state = next((x.expected_semantic_state for x in items if x.expected_semantic_state), "") or ""
        samples = len(items)
        exact_hits = sum(1 for x in items if x.agreed_symbol is True)
        semantic_hits = sum(1 for x in items if x.agreed_semantic_state is True)
        confidences = [x.confidence for x in items]

        out.append(
            PerSymbolSummary(
                symbol_id=symbol_id,
                semantic_state=semantic_state,
                samples=samples,
                exact_symbol_hits=exact_hits,
                semantic_hits=semantic_hits,
                exact_symbol_accuracy=(exact_hits / samples) if samples else 0.0,
                semantic_accuracy=(semantic_hits / samples) if samples else 0.0,
                mean_confidence=(sum(confidences) / samples) if samples else 0.0,
                min_confidence=min(confidences) if confidences else 0.0,
                max_confidence=max(confidences) if confidences else 0.0,
            )
        )

    out.sort(key=lambda x: x.symbol_id)
    return out


def build_confusion_matrix(
    cases: List[ValidationCase],
) -> Tuple[List[str], Dict[str, Dict[str, int]]]:
    labels = sorted(
        {
            x.expected_symbol_id
            for x in cases
            if x.expected_symbol_id
        }.union(
            {
                x.predicted_symbol_id
                for x in cases
                if x.predicted_symbol_id
            }
        )
    )

    matrix: Dict[str, Dict[str, int]] = {
        row: {col: 0 for col in labels}
        for row in labels
    }

    for case in cases:
        if not case.expected_symbol_id or not case.predicted_symbol_id:
            continue
        matrix[case.expected_symbol_id][case.predicted_symbol_id] += 1

    return labels, matrix


def overall_metrics(cases: List[ValidationCase]) -> Dict[str, Any]:
    comparable = [x for x in cases if x.agreed_symbol is not None]
    semantic_comparable = [x for x in cases if x.agreed_semantic_state is not None]

    exact_hits = sum(1 for x in comparable if x.agreed_symbol is True)
    semantic_hits = sum(1 for x in semantic_comparable if x.agreed_semantic_state is True)

    return {
        "samples_total": len(cases),
        "samples_with_expected_symbol": len(comparable),
        "samples_with_expected_semantic_state": len(semantic_comparable),
        "exact_symbol_hits": exact_hits,
        "semantic_hits": semantic_hits,
        "exact_symbol_accuracy": (exact_hits / len(comparable)) if comparable else 0.0,
        "semantic_accuracy": (semantic_hits / len(semantic_comparable)) if semantic_comparable else 0.0,
        "mean_confidence": (sum(x.confidence for x in cases) / len(cases)) if cases else 0.0,
        "mean_margin": (sum(x.margin for x in cases) / len(cases)) if cases else 0.0,
    }


# ---------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------
def write_cases_csv(path: Path, cases: List[ValidationCase]) -> None:
    fieldnames = [
        "source",
        "source_kind",
        "expected_symbol_id",
        "expected_semantic_state",
        "expected_phi",
        "expected_harmonics",
        "predicted_symbol_id",
        "predicted_name",
        "predicted_semantic_state",
        "predicted_phi",
        "predicted_harmonics",
        "confidence",
        "distance",
        "runner_up_symbol_id",
        "runner_up_confidence",
        "margin",
        "agreed_symbol",
        "agreed_semantic_state",
        "observation_pickup",
        "observation_stability",
        "observation_drift",
        "observation_phi",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases:
            writer.writerow(
                {
                    "source": case.source,
                    "source_kind": case.source_kind,
                    "expected_symbol_id": case.expected_symbol_id,
                    "expected_semantic_state": case.expected_semantic_state,
                    "expected_phi": "" if case.expected_phi is None else f"{case.expected_phi:.9f}",
                    "expected_harmonics": json.dumps(case.expected_harmonics) if case.expected_harmonics is not None else "",
                    "predicted_symbol_id": case.predicted_symbol_id,
                    "predicted_name": case.predicted_name,
                    "predicted_semantic_state": case.predicted_semantic_state,
                    "predicted_phi": "" if case.predicted_phi is None else f"{case.predicted_phi:.9f}",
                    "predicted_harmonics": json.dumps(case.predicted_harmonics) if case.predicted_harmonics is not None else "",
                    "confidence": f"{case.confidence:.6f}",
                    "distance": f"{case.distance:.6f}",
                    "runner_up_symbol_id": case.runner_up_symbol_id,
                    "runner_up_confidence": f"{case.runner_up_confidence:.6f}",
                    "margin": f"{case.margin:.6f}",
                    "agreed_symbol": case.agreed_symbol,
                    "agreed_semantic_state": case.agreed_semantic_state,
                    "observation_pickup": f"{case.observation_pickup:.6f}",
                    "observation_stability": f"{case.observation_stability:.6f}",
                    "observation_drift": f"{case.observation_drift:.6f}",
                    "observation_phi": "" if case.observation_phi is None else f"{case.observation_phi:.9f}",
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


def write_json_report(
    path: Path,
    catalog_path: Path,
    cases: List[ValidationCase],
    summaries: List[PerSymbolSummary],
    labels: List[str],
    matrix: Dict[str, Dict[str, int]],
    metrics: Dict[str, Any],
) -> None:
    payload = {
        "catalog": str(catalog_path),
        "overall_metrics": metrics,
        "per_symbol_summary": [asdict(x) for x in summaries],
        "confusion_matrix": {
            "labels": labels,
            "rows": matrix,
        },
        "cases": [asdict(x) for x in cases],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Symatics symbol write/read agreement from capture files"
    )
    parser.add_argument(
        "--catalog",
        default=str(OUTPUT_DIR / "symatics_symbol_catalog.json"),
        help="Path to symatics_symbol_catalog.json",
    )
    parser.add_argument(
        "--capture",
        nargs="+",
        required=True,
        help="One or more capture JSONL files",
    )
    parser.add_argument(
        "--expect",
        nargs="*",
        default=[],
        help='Optional explicit mapping entries like "capture_a.jsonl=S0"',
    )
    parser.add_argument(
        "--json-out",
        default=str(OUTPUT_DIR / "symatics_symbol_validation_report.json"),
        help="JSON report output path",
    )
    parser.add_argument(
        "--csv-out",
        default=str(OUTPUT_DIR / "symatics_symbol_validation_report.csv"),
        help="Per-case CSV output path",
    )
    parser.add_argument(
        "--matrix-out",
        default=str(OUTPUT_DIR / "symatics_symbol_validation_confusion_matrix.csv"),
        help="Confusion matrix CSV output path",
    )
    return parser


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    args = build_parser().parse_args()

    catalog_path = Path(args.catalog)
    capture_paths = [Path(p) for p in args.capture]
    json_out = Path(args.json_out)
    csv_out = Path(args.csv_out)
    matrix_out = Path(args.matrix_out)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    matrix_out.parent.mkdir(parents=True, exist_ok=True)

    catalog_payload = load_catalog(catalog_path)
    decoder = SymaticsSymbolDecoder(str(catalog_path))
    explicit_mapping = parse_expected_mapping(args.expect)

    cases: List[ValidationCase] = []

    for capture_path in capture_paths:
        decode_result = decoder.decode_capture(str(capture_path))

        expected_symbol = infer_expected_symbol(
            capture_path=capture_path,
            decoder_observation=decode_result.observation,
            catalog_payload=catalog_payload,
            explicit_mapping=explicit_mapping,
        )

        case = build_validation_case(
            capture_path=capture_path,
            decode_result=decode_result,
            expected_symbol=expected_symbol,
        )
        cases.append(case)

    summaries = per_symbol_summary(cases)
    labels, matrix = build_confusion_matrix(cases)
    metrics = overall_metrics(cases)

    write_json_report(
        path=json_out,
        catalog_path=catalog_path,
        cases=cases,
        summaries=summaries,
        labels=labels,
        matrix=matrix,
        metrics=metrics,
    )
    write_cases_csv(csv_out, cases)
    write_confusion_matrix_csv(matrix_out, labels, matrix)

    print("=== Symatics Symbol Validation ===")
    print(f"Catalog        : {catalog_path}")
    print(f"Catalog size   : {len(catalog_payload.get('symbols', []))}")
    print(f"Capture files  : {len(capture_paths)}")
    print()

    for case in cases:
        print(f"Source         : {Path(case.source).name}")
        print(f"Expected       : {case.expected_symbol_id} | {case.expected_semantic_state}")
        print(f"Predicted      : {case.predicted_symbol_id} | {case.predicted_name}")
        print(f"Semantic       : {case.predicted_semantic_state}")
        print(f"Confidence     : {case.confidence:.6f}")
        print(f"Distance       : {case.distance:.6f}")
        print(f"Runner-up      : {case.runner_up_symbol_id} | margin={case.margin:.6f}")
        print(f"Agree(symbol)  : {case.agreed_symbol}")
        print(f"Agree(semantic): {case.agreed_semantic_state}")
        print()

    print("Overall:")
    print(
        f"  exact_symbol_accuracy={metrics['exact_symbol_accuracy']:.6f} | "
        f"semantic_accuracy={metrics['semantic_accuracy']:.6f} | "
        f"mean_confidence={metrics['mean_confidence']:.6f}"
    )
    print()

    print("Per-symbol summary:")
    for s in summaries:
        print(
            f"  {s.symbol_id} | {s.semantic_state} | "
            f"samples={s.samples} | "
            f"exact={s.exact_symbol_accuracy:.6f} | "
            f"semantic={s.semantic_accuracy:.6f} | "
            f"mean_conf={s.mean_confidence:.6f}"
        )

    print()
    print(f"JSON   : {json_out}")
    print(f"CSV    : {csv_out}")
    print(f"Matrix : {matrix_out}")


if __name__ == "__main__":
    main()