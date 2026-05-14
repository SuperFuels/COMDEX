# ===============================
# 📁 backend/modules/codex/hardware/symbolic_qpu_isa.py
# ===============================
"""
Symbolic QPU ISA for CodexCore
--------------------------------
- Maps symbolic opcodes to Python execution stubs for SQS / GlyphCell
- Entanglement / superposition / collapse primitives
- Prediction forks / mutation / SQI hooks
- Metrics logging and production-ready integration
- YAML-compatible registry
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import time
import yaml
from uuid import uuid4
from hashlib import blake2s

from datetime import datetime  # kept (some older code paths reference it)
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms

# score_sqi can be circular in this repo; keep best-effort import
try:
    from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi  # type: ignore
except Exception:  # pragma: no cover
    score_sqi = None  # type: ignore


# -------------------------------
# Global runtime flags & metrics
# -------------------------------
GLOBAL_QPU_FLAGS: Dict[str, bool] = {
    "entangle_enabled": True,
    "collapse_enabled": True,
    "superpose_enabled": True,
    "metrics_enabled": True,
}

QPU_METRICS: Dict[str, float] = {
    "ops_executed": 0,
    "entangle_count": 0,
    "collapse_count": 0,
    "superpose_count": 0,
}


# -------------------------------
# Helper: Log metrics & timing
# -------------------------------
def log_qpu_op(op_name: str) -> float:
    """Log QPU opcode execution and track execution time."""
    start_time = time.time()
    if GLOBAL_QPU_FLAGS.get("metrics_enabled", False):
        QPU_METRICS["ops_executed"] += 1
        print(f"[QPU] Executed opcode: {op_name}")
    elapsed = time.time() - start_time
    QPU_METRICS[f"{op_name}_time"] = elapsed
    return elapsed


# -------------------------------
# Beam helpers (Phase 8)
# -------------------------------
def _new_beam_id(cell_id: str, stage: str) -> str:
    return f"beam_{cell_id}_{stage}_{uuid4().hex[:8]}"


def emit_beam(
    cell: GlyphCell,
    stage: str,
    payload: Any,
    context: Dict[str, Any],
    *,
    parent_id: Optional[str] = None,
    precision: Optional[str] = None,
    entanglement_ids: Optional[List[str]] = None,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Create & attach a lineage beam to a cell (predict/mutate/ingest/collapse/entangle)."""
    beam = {
        "beam_id": _new_beam_id(cell.id, stage),
        "parent_id": parent_id,
        "stage": stage,  # predict | mutate | ingest | collapse | entangle
        "timestamp": now_utc_iso(),
        "payload": payload,
        "precision": precision,
        "sqi": getattr(cell, "sqi_score", None),
        "entanglement_ids": list(entanglement_ids or []),
        "state": state or "active",
        "cell_id": cell.id,
    }
    waves = getattr(cell, "wave_beams", None)
    if waves is None:
        cell.wave_beams = []  # type: ignore[attr-defined]
    cell.wave_beams.append(beam)  # type: ignore[attr-defined]
    return beam


# -------------------------------
# Safe, lazy tokenizer import to avoid circulars during tests
# -------------------------------
try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs  # type: ignore
except Exception:  # pragma: no cover
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]


# -------------------------------
# EID helpers
# -------------------------------
def _compute_eid_for_cell(context: dict, cell: GlyphCell) -> str:
    sheet_run_id = context.get("sheet_run_id", "run")
    logic = (getattr(cell, "logic", "") or "")
    tokens = tokenize_symbol_text_to_glyphs(logic)
    sig = " ".join(t.get("value", "") for t in tokens)  # normalized opcode signature
    digest = blake2s(f"{sheet_run_id}::{sig}".encode("utf-8"), digest_size=8).hexdigest()
    return f"eid::{sheet_run_id}::{digest}"


def _append_eq_beam(cell: Optional[GlyphCell], stage: str, eid: str, payload: dict, context: dict) -> None:
    if not cell:
        return
    if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
        cell.wave_beams = []
    cell.wave_beams.append(
        {
            "beam_id": (
                f"beam_{cell.id}_eq_{stage}_{now_utc_ms()}"
                if getattr(cell, "id", None)
                else f"beam_eq_{stage}_{now_utc_ms()}"
            ),
            "source": "op_EQ",
            "stage": stage,  # entangle / predict / ingest / collapse
            "token": "↔",
            "eid": eid,
            "entanglement_ids": [eid],
            "payload": payload,
            "timestamp": now_utc_iso(),
        }
    )
    record_trace(getattr(cell, "id", "↔"), f"[Beam eq] stage={stage} eid={eid} payload={payload}")


# -------------------------------
# Core Opcode Implementations
# -------------------------------
def op_AND(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("AND ⊕")
    return [str(a) for a in args]


def op_EQ(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    EQUIVALENCE (↔)
    Phase 8:
      * Deterministically groups cells into an entanglement bucket per sheet run,
        using sheet_run_id + hash(normalized tokens).
      * Always records an entanglement entry & emits staged beams
        (entangle/predict/ingest/collapse), even with insufficient args.
    """
    log_qpu_op("EQUIVALENCE ↔")

    cell: Optional[GlyphCell] = context.get("cell")
    if cell:
        eid = _compute_eid_for_cell(context, cell)
    else:
        eid = f"eid::{context.get('sheet_run_id','run')}::anon"

    # ensure entanglement map entry (eid -> set(cell_ids))
    ent_map = context.setdefault("entanglements_map", {})
    if cell and getattr(cell, "id", None):
        ent_map.setdefault(eid, set()).add(cell.id)

    # record pairs if we actually got two args; otherwise keep lineage anyway
    if len(args) >= 2:
        a, b = args[0], args[1]
        context.setdefault("entangled_pairs", []).append((a, b))
        QPU_METRICS["entangle_count"] += 1
        payload: Dict[str, Any] = {"a": a, "b": b}
    else:
        payload = {"note": "insufficient_args"}

    # emit staged beams for lineage/visualizers
    for stage in ("entangle", "predict", "ingest", "collapse"):
        _append_eq_beam(cell, stage, eid, payload, context)

    if cell:
        cell.append_trace(f"[QPU] Entangled eid={eid}")

    # textual result (kept for compatibility with existing traces/tests)
    if len(args) >= 2:
        return [f"[Entangled {args[0]} ↔ {args[1]} eid={eid}]"]
    return [f"[Entangled eid={eid}]"]


def op_MUTATE(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("MUTATE ⟲")
    cell: Optional[GlyphCell] = context.get("cell")
    mutated = [f"{a}_mut" for a in args]
    if cell:
        emit_beam(cell, "mutate", {"before": args, "after": mutated}, context)
    return mutated


def op_DELAY(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("DELAY ⧖")
    return [f"[Delayed {args}]"]


def op_TRIGGER(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("TRIGGER ->")
    target = args[0] if args else "default_trigger"
    context.setdefault("triggered_ops", []).append(target)
    return [f"[Triggered {target}]"]


def op_COMPRESS(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("COMPRESS ∇c")
    return [f"[Compressed {args}]"]


def op_NEGATE(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("NEGATE ⊗")
    return [f"¬{a}" for a in args]


def op_MILESTONE(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("MILESTONE ✦")
    return [f"[Milestone {args}]"]


# -------------------------------
# G3: numeric ∇ (nabla) opcode for precision profiling
# -------------------------------
def _op_nabla(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> float:
    """
    Returns a stable-ish float so FP4/FP8/INT8 quantization creates measurable error.
    Design: golden-ratio base perturbed by a tiny cell-id fingerprint and mutation_score.
    """
    log_qpu_op("NABLA ∇")
    base = 0.6180339887498949  # φ - 1
    cell: Optional[GlyphCell] = context.get("cell")
    cid = getattr(cell, "id", "") if cell else ""
    cid_factor = (abs(hash(cid)) % 997) / 997.0 if cid else 0.0
    mutation = float(getattr(cell, "mutation_score", 0.0) or 0.0) if cell else 0.0
    return float(base * (1.0 + cid_factor * 0.1) + mutation * 0.001)


# -------------------------------
# Quantum Primitives (Stubs)
# -------------------------------
def apply_entanglement(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS.get("entangle_enabled", False):
        QPU_METRICS["entangle_count"] += 1
        cell.append_trace("🔗 Entanglement applied")
        return True
    return False


def apply_collapse(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS.get("collapse_enabled", False):
        QPU_METRICS["collapse_count"] += 1
        cell.append_trace("💥 Collapse triggered")
        return True
    return False


def apply_superpose(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS.get("superpose_enabled", False):
        QPU_METRICS["superpose_count"] += 1
        cell.append_trace("🔮 Superposition enabled")
        return True
    return False


# -------------------------------
# Prediction Fork Integration
# -------------------------------
def update_cell_prediction(cell: GlyphCell) -> List[str]:
    forks: List[str] = []
    base = cell.prediction or ""
    emo = (cell.emotion or "neutral").lower()

    if emo in ["curious", "inspired"]:
        forks.append(f"{base} + exploratory")
    elif emo in ["protective", "cautious"]:
        forks.append(f"{base} + conservative")
    else:
        forks.append(base)

    if "if" in (cell.logic or ""):
        forks.append(f"{base} | conditional path")

    cell.prediction_forks = forks
    cell.append_trace(f"🔮 Prediction forks updated: {forks}")

    ctx = getattr(cell, "_ctx", {}) or {}
    emit_beam(cell, "predict", {"forks": forks}, ctx)
    return forks


# -------------------------------
# Populate / update the opcode registry (single source of truth)
# -------------------------------
SYMBOLIC_QPU_OPS: Dict[str, Callable[..., Any]] = {
    "⊕": op_AND,
    "↔": op_EQ,
    "⟲": op_MUTATE,
    "⧖": op_DELAY,
    "->": op_TRIGGER,
    "∇": _op_nabla,     # profiling float opcode
    "∇c": op_COMPRESS,  # keep COMPRESS under alias
    "⊗": op_NEGATE,
    "✦": op_MILESTONE,
}


# -------------------------------
# Execute a single opcode
# -------------------------------
def execute_qpu_opcode(
    op: str,
    args: List[Any],
    cell: Optional[GlyphCell] = None,
    context: Optional[Dict[str, Any]] = None,
) -> List[str]:
    context = context or {}
    if not cell:
        cell = GlyphCell(id="unknown", logic="", position=[0, 0, 0, 0])

    # thread context into cell so update_cell_prediction can see it
    cell._ctx = context  # type: ignore[attr-defined]

    # resolve namespaced ops like "logic:↔" -> "↔"
    op_key = op
    if isinstance(op_key, str) and ":" in op_key:
        op_key = op_key.split(":", 1)[1]

    try:
        func = SYMBOLIC_QPU_OPS.get(op_key)
        if not func:
            return [f"[UnknownOpcode {op}]"]

        context["cell"] = cell
        result = func(args, context)

        ingest_beam = emit_beam(cell, "ingest", {"op": op, "args": args, "result": result}, context)

        apply_entanglement(cell)
        apply_collapse(cell)
        apply_superpose(cell)
        update_cell_prediction(cell)

        record_trace(cell.id, f"[QPU EXEC] {op}({args}) -> {result}")

        emit_beam(
            cell,
            "collapse",
            {"op": op, "result": result},
            context,
            parent_id=ingest_beam["beam_id"],
            state="collapsed",
        )

        # normalize return to List[str] for old callers/tests
        if isinstance(result, list):
            return [str(x) for x in result]
        return [str(result)]
    except Exception as e:
        record_trace(cell.id, f"[QPU Error] {op}: {e}")
        return [f"[Error {op}: {e}]"]


# -------------------------------
# Load opcode registry from YAML (optional)
# -------------------------------
def load_opcode_registry_from_yaml(filepath: str) -> None:
    global SYMBOLIC_QPU_OPS
    try:
        with open(filepath, "r") as f:
            opcodes_yaml = yaml.safe_load(f)

        # NOTE: YAML loader expects op['name'] -> function op_<name>
        loaded: Dict[str, Callable[..., Any]] = {}
        for opdef in opcodes_yaml or []:
            sym = opdef.get("symbol")
            nm = opdef.get("name")
            if not sym or not nm:
                continue
            fn = globals().get(f"op_{nm}")
            if callable(fn):
                loaded[str(sym)] = fn  # type: ignore[assignment]

        # merge: YAML overrides defaults
        SYMBOLIC_QPU_OPS = {**SYMBOLIC_QPU_OPS, **loaded}
        print(f"[QPU] Loaded {len(loaded)} opcodes from {filepath}")
    except Exception as e:
        print(f"[QPU Error] Failed to load YAML opcodes: {e}")


# -------------------------------
# Reset / Metrics Utilities
# -------------------------------
def reset_qpu_metrics() -> None:
    for key in list(QPU_METRICS.keys()):
        QPU_METRICS[key] = 0


def get_qpu_metrics() -> Dict[str, float]:
    return dict(QPU_METRICS)


# -------------------------------
# Standalone Test
# -------------------------------
if __name__ == "__main__":
    test_cell = GlyphCell(id="cell_001", logic="⊕ ↔ ⟲ -> ✦ ∇ ∇c", position=[0, 0])
    ctx: Dict[str, Any] = {"sheet_run_id": "run_demo"}
    print(execute_qpu_opcode("⊕", ["a", "b"], test_cell, ctx))
    print(execute_qpu_opcode("logic:↔", ["x", "y"], test_cell, ctx))
    print(execute_qpu_opcode("∇", [], test_cell, ctx))
    print(execute_qpu_opcode("∇c", ["data"], test_cell, ctx))
    print(get_qpu_metrics())