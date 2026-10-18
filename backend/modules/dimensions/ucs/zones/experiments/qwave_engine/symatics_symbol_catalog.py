from __future__ import annotations

"""
Symatics Symbol Catalog
-----------------------
Promote stable phase-map regions into a reusable symbol catalog.

Inputs
- CSV / JSON / JSONL from phase-map or sweep outputs

Outputs
- symatics_symbol_catalog.json
- symatics_symbol_catalog.csv

Purpose
- Take ranked stable symbolic regions
- De-duplicate near-identical phase neighborhoods
- Assign canonical symbol IDs
- Preserve lock/stability/response metrics
- Keep useful symbolic states even when strict locked=True was not achieved
- Prepare the next stage for decoder + write/read experiments

Update
- Phi identity keys now use 12 decimal places instead of 6 so fine-grained
  perturbation sweeps are not silently merged during catalog construction.
- Raw sweep JSONL rows are supported directly.
- phi_hint / harmonics_hint / nested observation metadata are now read.
- Fallback lock_quality is derived when no explicit quality field exists.
"""

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

TWO_PI = 2.0 * math.pi
PHI_KEY_DECIMALS = 12

CANONICAL_STATE_ORDER = [
    "constructive",
    "beyond_boolean_positive",
    "beyond_boolean_negative",
    "destructive",
    "intermediate",
]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _wrap_phase(phi: float) -> float:
    return float(phi) % TWO_PI


def _phase_distance(a: float, b: float) -> float:
    """Circular phase distance on [0, 2π)."""
    a = _wrap_phase(a)
    b = _wrap_phase(b)
    d = abs(a - b)
    return min(d, TWO_PI - d)


def _phi_identity(phi: float, decimals: int = PHI_KEY_DECIMALS) -> float:
    """
    Canonical phi key used for exact identity / de-dup bookkeeping.

    This is intentionally much finer than older 6-decimal identity keys, so
    nearby perturbation runs such as 3.141592995 vs 3.141593000 survive as
    distinct catalog entries when desired.
    """
    return round(_wrap_phase(phi), decimals)


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
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_harmonics(value: Any) -> List[int]:
    if value is None:
        return [1]

    if isinstance(value, list):
        out: List[int] = []
        for x in value:
            try:
                out.append(max(1, int(x)))
            except Exception:
                pass
        return out or [1]

    text = str(value).strip()
    if not text:
        return [1]

    if text.startswith("[") and text.endswith("]"):
        try:
            arr = json.loads(text)
            return _parse_harmonics(arr)
        except Exception:
            pass

    parts = [p.strip() for p in text.split(",") if p.strip()]
    out: List[int] = []
    for p in parts:
        try:
            out.append(max(1, int(float(p))))
        except Exception:
            pass
    return out or [1]


def _state_label(phi: float) -> str:
    phi = _wrap_phase(phi)
    if _phase_distance(phi, 0.0) < 0.15 or _phase_distance(phi, TWO_PI) < 0.15:
        return "constructive"
    if _phase_distance(phi, math.pi) < 0.15:
        return "destructive"
    if _phase_distance(phi, math.pi / 2.0) < 0.15:
        return "beyond_boolean_positive"
    if _phase_distance(phi, 3.0 * math.pi / 2.0) < 0.15:
        return "beyond_boolean_negative"
    return "intermediate"


def _state_priority(state: str) -> int:
    try:
        return CANONICAL_STATE_ORDER.index(state)
    except ValueError:
        return len(CANONICAL_STATE_ORDER)


def _harmonics_key(harmonics: Iterable[int]) -> str:
    return ",".join(str(int(h)) for h in harmonics)


def _canonical_symbol_name(state: str, harmonics: List[int], symbol_id: str) -> str:
    hk = _harmonics_key(harmonics).replace(",", "_")
    return f"{symbol_id}_{state}_{hk}"


def _candidate_admission_reason(
    cand: "RegionCandidate",
    min_stability: float,
    max_drift: float,
    min_quality: float,
    require_locked: bool,
    allow_unlocked_semantic_states: bool,
    allowed_states: Optional[set[str]],
) -> Tuple[bool, str]:
    state = cand.semantic_state

    if allowed_states is not None and state not in allowed_states:
        return False, f"state_not_allowed:{state}"

    if cand.stability < min_stability:
        return False, f"stability_below_threshold:{cand.stability:.6f}"

    if cand.drift > max_drift:
        return False, f"drift_above_threshold:{cand.drift:.6f}"

    if cand.lock_quality < min_quality:
        return False, f"quality_below_threshold:{cand.lock_quality:.6f}"

    if require_locked and not cand.locked:
        if not (
            allow_unlocked_semantic_states
            and state in {
                "constructive",
                "destructive",
                "beyond_boolean_positive",
                "beyond_boolean_negative",
            }
        ):
            return False, "locked_required"

    return True, "accepted"


# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------
@dataclass(slots=True)
class RegionCandidate:
    phi: float
    harmonics: List[int]
    stability: float
    lock_quality: float
    drift: float
    mean_pickup: float
    pickup_std: float
    ticks: int
    locked: bool
    source_row: Dict[str, Any]

    @property
    def semantic_state(self) -> str:
        return _state_label(self.phi)

    @property
    def normalized_pickup(self) -> float:
        return max(0.0, self.mean_pickup)

    @property
    def rank_score(self) -> float:
        """
        Overall score used for ranking symbolic regions.

        Emphasis:
        - stability
        - lock_quality / quality
        - pickup strength
        - low drift
        - modest bonus for actual locked states
        """
        drift_penalty = max(0.0, self.drift)
        lock_bonus = 0.25 if self.locked else 0.0
        return (
            (self.stability * 2.0)
            + (self.lock_quality * 1.5)
            + (self.normalized_pickup * 0.75)
            + lock_bonus
            - (drift_penalty * 8.0)
        )


@dataclass(slots=True)
class CatalogSymbol:
    symbol_id: str
    name: str
    semantic_state: str
    phi: float
    phi_degrees: float
    harmonics: List[int]
    stability: float
    lock_quality: float
    drift: float
    mean_pickup: float
    pickup_std: float
    ticks: int
    locked: bool
    rank_score: float
    notes: Dict[str, Any]


# ---------------------------------------------------------------------
# Input normalization
# ---------------------------------------------------------------------
def _coerce_source_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten common raw sweep shapes into a single observation-like dict while
    preserving the original row for notes/debugging.
    """
    obs = row.get("observation")
    if isinstance(obs, dict):
        meta = obs.get("metadata", {})
        merged = {}
        if isinstance(meta, dict):
            merged.update(meta)
        merged.update(obs)
        # keep top-level prediction-ish fields too
        for k, v in row.items():
            if k != "observation":
                merged.setdefault(k, v)
        return merged

    return dict(row)


def _normalize_row(row: Dict[str, Any]) -> Optional[RegionCandidate]:
    """
    Accept multiple possible schemas from symatics_phase_map.py and raw sweep
    JSON/JSONL outputs.
    """
    src = _coerce_source_dict(row)

    phi = _safe_float(
        src.get("phi_hint")
        or src.get("phi")
        or src.get("phase")
        or src.get("phase_radians")
        or src.get("phase_rad")
        or 0.0,
        default=0.0,
    )

    harmonics = _parse_harmonics(
        src.get("harmonics_hint")
        or src.get("harmonics")
        or src.get("harmonic_signature")
        or src.get("harmonic_set")
        or src.get("harmonic_set_key")
        or src.get("harmonic")
    )

    stability = _safe_float(
        src.get("stability")
        or src.get("stability_mean")
        or src.get("mean_stability")
        or src.get("stability_score")
        or src.get("avg_stability")
        or 0.0,
        default=0.0,
    )

    raw_lock_quality = (
        src.get("lock_quality")
        or src.get("quality")
        or src.get("quality_score")
        or src.get("score")
    )
    lock_quality = _safe_float(raw_lock_quality, default=math.nan)

    drift = _safe_float(
        src.get("drift")
        or src.get("phase_drift")
        or src.get("mean_drift")
        or src.get("drift_value")
        or 999.0,
        default=999.0,
    )

    mean_pickup = _safe_float(
        src.get("mean_pickup")
        or src.get("pickup_mean")
        or src.get("pickup_voltage_mean")
        or src.get("pickup")
        or src.get("pickup_mean_abs")
        or src.get("mean_response")
        or 0.0,
        default=0.0,
    )

    pickup_std = _safe_float(
        src.get("pickup_std")
        or src.get("pickup_voltage_std")
        or src.get("std_pickup")
        or src.get("response_std")
        or 0.0,
        default=0.0,
    )

    ticks = _safe_int(
        src.get("ticks")
        or src.get("tick_count")
        or src.get("samples")
        or 0,
        default=0,
    )

    locked = _safe_bool(
        src.get("locked")
        or src.get("is_locked")
        or src.get("lock")
        or False,
        default=False,
    )

    if not math.isfinite(lock_quality):
        # Fallback quality for raw sweep rows that do not carry an explicit
        # quality field.
        lock_quality = max(
            0.0,
            (
                stability * 2.0
                + mean_pickup * 2.0
                - drift * 10.0
                + (0.25 if locked else 0.0)
            ),
        )

    return RegionCandidate(
        phi=_wrap_phase(phi),
        harmonics=harmonics,
        stability=stability,
        lock_quality=lock_quality,
        drift=drift,
        mean_pickup=mean_pickup,
        pickup_std=pickup_std,
        ticks=ticks,
        locked=locked,
        source_row=dict(row),
    )


def _load_csv(path: Path) -> List[RegionCandidate]:
    out: List[RegionCandidate] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cand = _normalize_row(row)
            if cand is not None:
                out.append(cand)
    return out


def _load_json(path: Path) -> List[RegionCandidate]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]]

    if isinstance(data, list):
        rows = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        if isinstance(data.get("regions"), list):
            rows = [x for x in data["regions"] if isinstance(x, dict)]
        elif isinstance(data.get("results"), list):
            rows = [x for x in data["results"] if isinstance(x, dict)]
        elif isinstance(data.get("rows"), list):
            rows = [x for x in data["rows"] if isinstance(x, dict)]
        elif isinstance(data.get("symbols"), list):
            rows = [x for x in data["symbols"] if isinstance(x, dict)]
        else:
            rows = [data]
    else:
        rows = []

    out: List[RegionCandidate] = []
    for row in rows:
        cand = _normalize_row(row)
        if cand is not None:
            out.append(cand)
    return out


def _load_jsonl(path: Path) -> List[RegionCandidate]:
    out: List[RegionCandidate] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                cand = _normalize_row(row)
                if cand is not None:
                    out.append(cand)
    return out


def load_candidates(path: Path) -> List[RegionCandidate]:
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return _load_csv(path)
    if suffix == ".json":
        return _load_json(path)
    if suffix == ".jsonl":
        return _load_jsonl(path)

    raise ValueError("Input must be .csv, .json, or .jsonl")


# ---------------------------------------------------------------------
# Catalog construction
# ---------------------------------------------------------------------
def dedupe_candidates(
    candidates: List[RegionCandidate],
    phi_merge_threshold: float = 0.18,
) -> List[RegionCandidate]:
    """
    Keep the strongest representative for each nearby phase neighborhood
    per harmonic signature.

    This uses circular distance, not rounded phi identity keys, so coarse or
    fine exact-key rounding changes do not alter semantic neighborhood dedupe.
    """
    ordered = sorted(candidates, key=lambda x: x.rank_score, reverse=True)
    selected: List[RegionCandidate] = []

    for cand in ordered:
        duplicate = False
        for keep in selected:
            same_harmonics = keep.harmonics == cand.harmonics
            near_phase = _phase_distance(keep.phi, cand.phi) <= phi_merge_threshold
            if same_harmonics and near_phase:
                duplicate = True
                break

        if not duplicate:
            selected.append(cand)

    return selected


def _choose_best_per_state(
    candidates: List[RegionCandidate],
    require_states: List[str],
) -> List[RegionCandidate]:
    chosen: List[RegionCandidate] = []
    for state in require_states:
        pool = [c for c in candidates if c.semantic_state == state]
        if not pool:
            continue
        best = max(pool, key=lambda c: c.rank_score)
        chosen.append(best)
    return chosen


def build_catalog(
    candidates: List[RegionCandidate],
    min_stability: float = 0.80,
    max_drift: float = 0.10,
    min_quality: float = 2.5,
    require_locked: bool = False,
    allow_unlocked_semantic_states: bool = True,
    max_symbols: int = 16,
    phi_merge_threshold: float = 0.18,
    require_state_coverage: bool = True,
) -> List[CatalogSymbol]:
    allowed_states = {
        "constructive",
        "destructive",
        "beyond_boolean_positive",
        "beyond_boolean_negative",
        "intermediate",
    }

    admitted: List[RegionCandidate] = []
    for cand in candidates:
        ok, _reason = _candidate_admission_reason(
            cand=cand,
            min_stability=min_stability,
            max_drift=max_drift,
            min_quality=min_quality,
            require_locked=require_locked,
            allow_unlocked_semantic_states=allow_unlocked_semantic_states,
            allowed_states=allowed_states,
        )
        if ok:
            admitted.append(cand)

    deduped = dedupe_candidates(admitted, phi_merge_threshold=phi_merge_threshold)

    selected: List[RegionCandidate] = []

    if require_state_coverage:
        required_states = [
            "constructive",
            "beyond_boolean_positive",
            "beyond_boolean_negative",
            "destructive",
        ]
        selected.extend(_choose_best_per_state(deduped, required_states))

    seen_keys = {
        (_harmonics_key(c.harmonics), _phi_identity(c.phi))
        for c in selected
    }

    remaining = sorted(
        deduped,
        key=lambda c: (
            _state_priority(c.semantic_state),
            -c.rank_score,
        ),
    )

    for cand in remaining:
        if len(selected) >= max_symbols:
            break
        key = (_harmonics_key(cand.harmonics), _phi_identity(cand.phi))
        if key in seen_keys:
            continue
        selected.append(cand)
        seen_keys.add(key)

    ranked = sorted(
        selected,
        key=lambda c: (
            _state_priority(c.semantic_state),
            -c.rank_score,
            len(c.harmonics),
            c.phi,
        ),
    )[:max_symbols]

    catalog: List[CatalogSymbol] = []
    for idx, cand in enumerate(ranked):
        symbol_id = f"S{idx}"
        semantic = cand.semantic_state
        name = _canonical_symbol_name(semantic, cand.harmonics, symbol_id)

        catalog.append(
            CatalogSymbol(
                symbol_id=symbol_id,
                name=name,
                semantic_state=semantic,
                phi=cand.phi,
                phi_degrees=(cand.phi * 180.0 / math.pi),
                harmonics=cand.harmonics,
                stability=cand.stability,
                lock_quality=cand.lock_quality,
                drift=cand.drift,
                mean_pickup=cand.mean_pickup,
                pickup_std=cand.pickup_std,
                ticks=cand.ticks,
                locked=cand.locked,
                rank_score=cand.rank_score,
                notes={
                    "harmonics_key": _harmonics_key(cand.harmonics),
                    "phi_identity": _phi_identity(cand.phi),
                    "phi_identity_decimals": PHI_KEY_DECIMALS,
                    "source_fields": sorted(list(cand.source_row.keys())),
                    "allow_unlocked_semantic_states": allow_unlocked_semantic_states,
                    "admission_profile": "semantic_region_catalog_v4",
                },
            )
        )

    return catalog


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------
def write_catalog_json(
    path: Path,
    catalog: List[CatalogSymbol],
    source_path: Path,
) -> None:
    payload = {
        "source": str(source_path),
        "symbol_count": len(catalog),
        "phi_identity_decimals": PHI_KEY_DECIMALS,
        "symbols": [asdict(sym) for sym in catalog],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_catalog_csv(path: Path, catalog: List[CatalogSymbol]) -> None:
    fieldnames = [
        "symbol_id",
        "name",
        "semantic_state",
        "phi",
        "phi_degrees",
        "harmonics",
        "stability",
        "lock_quality",
        "drift",
        "mean_pickup",
        "pickup_std",
        "ticks",
        "locked",
        "rank_score",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for sym in catalog:
            writer.writerow(
                {
                    "symbol_id": sym.symbol_id,
                    "name": sym.name,
                    "semantic_state": sym.semantic_state,
                    "phi": f"{sym.phi:.12f}",
                    "phi_degrees": f"{sym.phi_degrees:.6f}",
                    "harmonics": json.dumps(sym.harmonics),
                    "stability": f"{sym.stability:.6f}",
                    "lock_quality": f"{sym.lock_quality:.6f}",
                    "drift": f"{sym.drift:.6f}",
                    "mean_pickup": f"{sym.mean_pickup:.6f}",
                    "pickup_std": f"{sym.pickup_std:.6f}",
                    "ticks": sym.ticks,
                    "locked": sym.locked,
                    "rank_score": f"{sym.rank_score:.6f}",
                }
            )


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build canonical symbols from a symatics phase map"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(OUTPUT_DIR / "symatics_phase_map.csv"),
        help="Input CSV / JSON / JSONL from symatics phase map or raw sweep output",
    )
    parser.add_argument(
        "--min-stability",
        type=float,
        default=0.80,
        help="Minimum stability required to admit a symbol",
    )
    parser.add_argument(
        "--max-drift",
        type=float,
        default=0.10,
        help="Maximum drift allowed to admit a symbol",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=2.50,
        help="Minimum quality / lock_quality required to admit a symbol",
    )
    parser.add_argument(
        "--require-locked",
        action="store_true",
        help="Require locked=True for symbol admission",
    )
    parser.add_argument(
        "--disallow-unlocked-semantic-states",
        action="store_true",
        help="Do not allow semantic anchor states unless they are locked",
    )
    parser.add_argument(
        "--no-state-coverage",
        action="store_true",
        help=(
            "Do not force inclusion of best representatives for "
            "constructive / beyond / destructive states"
        ),
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=16,
        help="Maximum number of canonical symbols to emit",
    )
    parser.add_argument(
        "--phi-merge-threshold",
        type=float,
        default=0.18,
        help="Circular phase distance threshold for de-duplication",
    )
    parser.add_argument(
        "--json-out",
        default=str(OUTPUT_DIR / "symatics_symbol_catalog.json"),
        help="Catalog JSON output path",
    )
    parser.add_argument(
        "--csv-out",
        default=str(OUTPUT_DIR / "symatics_symbol_catalog.csv"),
        help="Catalog CSV output path",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    input_path = Path(args.input)
    json_out = Path(args.json_out)
    csv_out = Path(args.csv_out)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    csv_out.parent.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates(input_path)
    catalog = build_catalog(
        candidates=candidates,
        min_stability=args.min_stability,
        max_drift=args.max_drift,
        min_quality=args.min_quality,
        require_locked=args.require_locked,
        allow_unlocked_semantic_states=not args.disallow_unlocked_semantic_states,
        max_symbols=args.max_symbols,
        phi_merge_threshold=args.phi_merge_threshold,
        require_state_coverage=not args.no_state_coverage,
    )

    write_catalog_json(json_out, catalog, input_path)
    write_catalog_csv(csv_out, catalog)

    print("=== Symatics Symbol Catalog ===")
    print(f"Input               : {input_path}")
    print(f"Candidates          : {len(candidates)}")
    print(f"Catalog count       : {len(catalog)}")
    print(f"Phi identity digits : {PHI_KEY_DECIMALS}")
    print()

    for sym in catalog:
        print(
            f"{sym.symbol_id} | {sym.semantic_state} | "
            f"phi={sym.phi:.12f} | deg={sym.phi_degrees:.2f} | "
            f"harmonics={sym.harmonics} | "
            f"stability={sym.stability:.6f} | "
            f"quality={sym.lock_quality:.6f} | "
            f"drift={sym.drift:.6f} | "
            f"pickup={sym.mean_pickup:.6f} | "
            f"rank={sym.rank_score:.6f} | "
            f"locked={sym.locked}"
        )

    print()
    print(f"JSON: {json_out}")
    print(f"CSV : {csv_out}")


if __name__ == "__main__":
    main()