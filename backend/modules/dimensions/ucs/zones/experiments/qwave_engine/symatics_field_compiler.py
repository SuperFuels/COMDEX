from __future__ import annotations

"""
Symatics Field Compiler
-----------------------
Minimal stable compiler layer for Symatics field programs.

Responsibilities
1. compile symbol -> emission program
2. attach expected signature metadata
3. provide a stable object for engine + trials + hardware tests

This module is intentionally small and conservative.
It does not replace the engine compiler. It wraps the catalog and emits a
normalized program object that other layers can consume consistently.

Typical usage
-------------
    compiler = SymaticsFieldCompiler()
    program = compiler.compile_symbol("S2")

    # Send to engine compiler
    expr = program.to_expression(engine.compiler)

    # Use attached expectations in trials / hardware assertions
    print(program.expected_signature.semantic_state)
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


OUTPUT_DIR = Path(
    "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
)

DEFAULT_CATALOG_PATH = OUTPUT_DIR / "symatics_symbol_catalog.json"


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
    phi_degrees: float
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
class ExpectedFieldSignature:
    """
    Expected measured signature attached to an emitted program.
    This is the important bridge object for trials / decoder / hardware tests.
    """
    symbol_id: str
    symbol_name: str
    semantic_state: str
    phi: float
    phi_degrees: float
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

    aux_adc_1_mean: float = 0.0
    aux_adc_2_mean: float = 0.0
    magnetometer_x_mean: float = 0.0
    magnetometer_y_mean: float = 0.0
    magnetometer_z_mean: float = 0.0

    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FieldEmissionProgram:
    """
    Stable compiled object for engine + trials + hardware tests.
    """
    symbol_id: str
    symbol_name: str
    semantic_state: str

    phi: float
    harmonics: List[int]
    amplitude: float
    frequency: float
    duty_cycle: float
    envelope: str

    expected_signature: ExpectedFieldSignature
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_expression(self, compiler: Any) -> Any:
        """
        Convert this stable program into the engine/compiler expression.
        Expects the supplied compiler to expose .phase_probe(...).
        """
        if not hasattr(compiler, "phase_probe"):
            raise AttributeError("Compiler object must provide phase_probe(...)")

        return compiler.phase_probe(
            phi=self.phi,
            frequency=self.frequency,
            amplitude=self.amplitude,
            harmonics=self.harmonics,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------
def load_symbol_catalog(path: Path) -> Dict[str, CatalogSymbol]:
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("symbols"), list):
        rows = payload["symbols"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError(
            "Catalog JSON must contain a top-level 'symbols' list or be a list"
        )

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

        phi = _safe_float(row.get("phi"), 0.0)
        phi_degrees = _safe_float(
            row.get("phi_degrees", row.get("phi_deg", 0.0)),
            0.0,
        )

        out[symbol_id] = CatalogSymbol(
            symbol_id=symbol_id,
            name=str(row.get("name", symbol_id)),
            semantic_state=str(row.get("semantic_state", "unknown")),
            phi=phi,
            phi_degrees=phi_degrees,
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
# Field compiler
# ---------------------------------------------------------------------
class SymaticsFieldCompiler:
    """
    Minimal stable compiler wrapper around the symbol catalog.

    It does not try to be the waveform compiler itself.
    It turns a catalog symbol into a normalized FieldEmissionProgram.
    """

    def __init__(self, catalog_path: str | Path = DEFAULT_CATALOG_PATH):
        self.catalog_path = Path(catalog_path)
        self.catalog = load_symbol_catalog(self.catalog_path)

    def has_symbol(self, symbol_id: str) -> bool:
        return symbol_id in self.catalog

    def get_symbol(self, symbol_id: str) -> CatalogSymbol:
        try:
            return self.catalog[symbol_id]
        except KeyError as exc:
            known = ", ".join(sorted(self.catalog.keys()))
            raise KeyError(f"Unknown symbol_id='{symbol_id}'. Known: {known}") from exc

    def expected_signature_for(self, symbol_id: str) -> ExpectedFieldSignature:
        sym = self.get_symbol(symbol_id)
        notes = sym.notes or {}

        return ExpectedFieldSignature(
            symbol_id=sym.symbol_id,
            symbol_name=sym.name,
            semantic_state=sym.semantic_state,
            phi=sym.phi,
            phi_degrees=sym.phi_degrees,
            harmonics=list(sym.harmonics),
            stability=sym.stability,
            lock_quality=sym.lock_quality,
            drift=sym.drift,
            mean_pickup=sym.mean_pickup,
            pickup_std=sym.pickup_std,
            voltage_mean=sym.voltage_mean,
            ticks=sym.ticks,
            locked=sym.locked,
            rank_score=sym.rank_score,
            aux_adc_1_mean=_safe_float(notes.get("aux_adc_1_mean"), 0.0),
            aux_adc_2_mean=_safe_float(notes.get("aux_adc_2_mean"), 0.0),
            magnetometer_x_mean=_safe_float(notes.get("magnetometer_x_mean"), 0.0),
            magnetometer_y_mean=_safe_float(notes.get("magnetometer_y_mean"), 0.0),
            magnetometer_z_mean=_safe_float(notes.get("magnetometer_z_mean"), 0.0),
            notes=dict(notes),
        )

    def compile_symbol(
        self,
        symbol_id: str,
        *,
        amplitude: float = 1.0,
        frequency: float = 1.0,
        duty_cycle: float = 0.5,
        envelope: str = "steady",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FieldEmissionProgram:
        """
        Compile a catalog symbol into a stable emission program object.
        """
        sym = self.get_symbol(symbol_id)
        signature = self.expected_signature_for(symbol_id)

        merged_metadata: Dict[str, Any] = {
            "catalog_path": str(self.catalog_path),
            "compiled_from": "symatics_symbol_catalog",
            "symbol_id": sym.symbol_id,
            "symbol_name": sym.name,
            "semantic_state": sym.semantic_state,
        }
        if metadata:
            merged_metadata.update(dict(metadata))

        return FieldEmissionProgram(
            symbol_id=sym.symbol_id,
            symbol_name=sym.name,
            semantic_state=sym.semantic_state,
            phi=sym.phi,
            harmonics=list(sym.harmonics),
            amplitude=float(amplitude),
            frequency=float(frequency),
            duty_cycle=float(duty_cycle),
            envelope=str(envelope),
            expected_signature=signature,
            metadata=merged_metadata,
        )

    def compile_many(
        self,
        symbol_ids: List[str],
        *,
        amplitude: float = 1.0,
        frequency: float = 1.0,
        duty_cycle: float = 0.5,
        envelope: str = "steady",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[FieldEmissionProgram]:
        return [
            self.compile_symbol(
                symbol_id=symbol_id,
                amplitude=amplitude,
                frequency=frequency,
                duty_cycle=duty_cycle,
                envelope=envelope,
                metadata=metadata,
            )
            for symbol_id in symbol_ids
        ]

    def program_for_engine(
        self,
        symbol_id: str,
        engine: Any,
        *,
        amplitude: float = 1.0,
        frequency: float = 1.0,
        duty_cycle: float = 0.5,
        envelope: str = "steady",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[FieldEmissionProgram, Any]:
        """
        Convenience wrapper:
        returns (stable_program, engine_expression)
        """
        program = self.compile_symbol(
            symbol_id=symbol_id,
            amplitude=amplitude,
            frequency=frequency,
            duty_cycle=duty_cycle,
            envelope=envelope,
            metadata=metadata,
        )

        compiler = getattr(engine, "compiler", None)
        if compiler is None:
            raise AttributeError("Engine must expose .compiler")

        expr = program.to_expression(compiler)
        return program, expr