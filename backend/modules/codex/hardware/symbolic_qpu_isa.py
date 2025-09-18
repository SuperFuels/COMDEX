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

from typing import Any, Dict, List, Optional
import time
import yaml
from datetime import datetime
from uuid import uuid4
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms

# -------------------------------
# Global runtime flags & metrics
# -------------------------------
GLOBAL_QPU_FLAGS: Dict[str, bool] = {
    "entangle_enabled": True,
    "collapse_enabled": True,
    "superpose_enabled": True,
    "metrics_enabled": True
}

QPU_METRICS: Dict[str, float] = {
    "ops_executed": 0,
    "entangle_count": 0,
    "collapse_count": 0,
    "superpose_count": 0
}

# -------------------------------
# Helper: Log metrics & timing
# -------------------------------
def log_qpu_op(op_name: str) -> float:
    """Log QPU opcode execution and track execution time."""
    start_time = time.time()
    if GLOBAL_QPU_FLAGS["metrics_enabled"]:
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
    state: Optional[str] = None
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
# Core Opcode Implementations
# -------------------------------
def op_AND(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("AND ⊕")
    return [str(a) for a in args]

# ── top of file (imports) ─────────────────────────────────────────────────────────
from hashlib import blake2s

# safe, lazy tokenizer import to avoid circulars during tests
try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
except Exception:
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]

# ── helper: compute deterministic EID from sheet_run_id + normalized tokens ──────
def _compute_eid_for_cell(context: dict, cell) -> str:
    sheet_run_id = context.get("sheet_run_id", "run")
    logic = (getattr(cell, "logic", "") or "")
    tokens = tokenize_symbol_text_to_glyphs(logic)
    sig = " ".join(t.get("value", "") for t in tokens)  # normalized opcode signature
    digest = blake2s(f"{sheet_run_id}::{sig}".encode("utf-8"), digest_size=8).hexdigest()
    return f"eid::{sheet_run_id}::{digest}"

# ── helper: append an EQ beam with stage + entanglement tag ──────────────────────
def _append_eq_beam(cell, stage: str, eid: str, payload: dict, context: dict) -> None:
    if not cell:
        return
    if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
        cell.wave_beams = []
    cell.wave_beams.append({
        "beam_id": (
            f"beam_{cell.id}_eq_{stage}_{now_utc_ms()}"
            if getattr(cell, "id", None) else
            f"beam_eq_{stage}_{now_utc_ms()}"
        ),
        "source": "op_EQ",
        "stage": stage,          # predict / ingest / collapse
        "token": "↔",
        "eid": eid,
        "entanglement_ids": [eid],
        "payload": payload,
        "timestamp": now_utc_iso(),
    })
    record_trace(getattr(cell, "id", "↔"), f"[Beam eq/entangle] stage={stage} eid={eid} payload={payload}")

# ── replace the existing op_EQ with this version ─────────────────────────────────
def op_EQ(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    EQUIVALENCE (↔)
    Phase 8:
      • Deterministically groups cells into an entanglement bucket per sheet run,
        using sheet_run_id + hash(normalized tokens).
      • Always records an entanglement entry & emits staged beams
        (entangle/predict/ingest/collapse), even with insufficient args.
    """
    log_qpu_op("EQUIVALENCE ↔")

    cell: Optional[GlyphCell] = context.get("cell")
    eid = _compute_eid_for_cell(context, cell) if cell else f"eid::{context.get('sheet_run_id','run')}::anon"

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

    # emit staged beams for lineage/visualizers (now includes 'entangle')
    for stage in ("entangle", "predict", "ingest", "collapse"):
        _append_eq_beam(cell, stage, eid, payload, context)

    if cell:
        cell.append_trace(f"[QPU] Entangled eid={eid}")

    # textual result (kept for compatibility with existing traces/tests)
    if len(args) >= 2:
        return [f"[Entangled {args[0]} ↔ {args[1]} eid={eid}]"]
    else:
        return [f"[Entangled eid={eid}]"]

    # local safe beam emit (avoids circular imports)
    def _emit_beam(stage: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            beam = {
                "beam_id": f"beam_{cell.id}_eq_{stage}_{int(datetime.utcnow().timestamp()*1000)}" if cell else
                           f"beam_unknown_eq_{stage}_{int(datetime.utcnow().timestamp()*1000)}",
                "stage": stage,
                "source": "qpu_op_EQ",
                "token": {"type": "operator", "value": "↔"},
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat(),
                "entanglement_ids": [eid],
            }
            if cell:
                getattr(cell, "wave_beams", []).append(beam)
            record_trace(getattr(cell, "id", "sheet"), f"[Beam eq/{stage}] eid={eid} payload={payload}")
            return beam
        except Exception as _e:
            record_trace(getattr(cell, "id", "sheet"), f"[QPU eq beam error] {str(_e)}")
            return {"beam_id": "beam_error", "stage": stage, "entanglement_ids": [eid], "error": str(_e)}

    # If insufficient args, still register entanglement + emit a minimal entangle beam.
    if not cell or len(args) < 2:
        beam = _emit_beam("entangle", {"note": "insufficient_args"})
        return [f"[EQ ERROR: Need 2 args]"]

    # Legacy/normal behavior when args are provided
    a, b = args[0], args[1]
    context.setdefault("entangled_pairs", []).append((a, b))
    QPU_METRICS["entangle_count"] += 1

    beam = _emit_beam("entangle", {"a": a, "b": b})
    cell.append_trace(f"[QPU] Entangled {a} ↔ {b} eid={eid}")
    return [f"[Entangled {a} ↔ {b} eid={eid} beam={beam['beam_id']}]"]

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
    log_qpu_op("TRIGGER →")
    target = args[0] if args else "default_trigger"
    context.setdefault("triggered_ops", []).append(target)
    return [f"[Triggered {target}]"]

def op_COMPRESS(args: List[Any], context: Dict[str, Any], registers: Optional[Dict[str, Any]] = None) -> List[str]:
    log_qpu_op("COMPRESS ∇")
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
    # stable per-process but deterministic fingerprint
    cid_factor = (abs(hash(cid)) % 997) / 997.0 if cid else 0.0
    mutation = float(getattr(cell, "mutation_score", 0.0) or 0.0) if cell else 0.0
    return float(base * (1.0 + cid_factor * 0.1) + mutation * 0.001)

# -------------------------------
# Quantum Primitives (Stubs)
# -------------------------------
def apply_entanglement(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS["entangle_enabled"]:
        QPU_METRICS["entangle_count"] += 1
        cell.append_trace("🔗 Entanglement applied")
        return True
    return False

def apply_collapse(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS["collapse_enabled"]:
        QPU_METRICS["collapse_count"] += 1
        cell.append_trace("💥 Collapse triggered")
        return True
    return False

def apply_superpose(cell: GlyphCell) -> bool:
    if GLOBAL_QPU_FLAGS["superpose_enabled"]:
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

    # Phase 8: emit predict beam
    ctx = getattr(cell, "_ctx", {}) or {}
    emit_beam(cell, "predict", {"forks": forks}, ctx)
    return forks

# -------------------------------
# Execute a single opcode
# -------------------------------
def execute_qpu_opcode(
    op: str,
    args: List[Any],
    cell: Optional[GlyphCell] = None,
    context: Optional[Dict[str, Any]] = None
) -> List[str]:
    context = context or {}
    if not cell:
        cell = GlyphCell(id="unknown", logic="", position=[0,0,0,0])

    # thread context into cell so update_cell_prediction can see it
    cell._ctx = context  # type: ignore[attr-defined]

    try:
        func = SYMBOLIC_QPU_OPS.get(op)
        if not func:
            return [f"[UnknownOpcode {op}]"]

        context["cell"] = cell
        result = func(args, context)

        # ingest beam (op result)
        ingest_beam = emit_beam(cell, "ingest", {"op": op, "args": args, "result": result}, context)

        # quantum stubs + traces (unchanged)
        apply_entanglement(cell)
        apply_collapse(cell)
        apply_superpose(cell)
        update_cell_prediction(cell)
        record_trace(cell.id, f"[QPU EXEC] {op}({args}) → {result}")

        # collapse beam (after collapse stage)
        emit_beam(cell, "collapse", {"op": op, "result": result}, context, parent_id=ingest_beam["beam_id"], state="collapsed")

        return result
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
        SYMBOLIC_QPU_OPS = {
            op["symbol"]: globals().get(f"op_{op['name']}", lambda a,c,r=None: [f"[Stub]"])
            for op in opcodes_yaml
        }
        print(f"[QPU] Loaded {len(SYMBOLIC_QPU_OPS)} opcodes from {filepath}")
    except Exception as e:
        print(f"[QPU Error] Failed to load YAML opcodes: {e}")

# -------------------------------
# Populate / update the opcode registry
# -------------------------------
SYMBOLIC_QPU_OPS: Dict[str, Any] = {
    "⊕": op_AND,
    "↔": op_EQ,
    "⟲": op_MUTATE,
    "⧖": op_DELAY,
    "→": op_TRIGGER,
    # G3: numeric profiling opcode
    "∇": _op_nabla,
    # keep COMPRESS available under an alias to avoid functionality loss
    "∇c": op_COMPRESS,
    "⊗": op_NEGATE,
    "✦": op_MILESTONE,
}

# Override / add numeric ∇ mapping for profiling (G3)
SYMBOLIC_QPU_OPS["∇"] = _op_nabla

# -------------------------------
# Reset / Metrics Utilities
# -------------------------------
def reset_qpu_metrics() -> None:
    for key in QPU_METRICS:
        QPU_METRICS[key] = 0

def get_qpu_metrics() -> Dict[str, float]:
    return dict(QPU_METRICS)

# -------------------------------
# Standalone Test
# -------------------------------
if __name__ == "__main__":
    test_cell = GlyphCell(id="cell_001", logic="⊕ ↔ ⟲ → ✦ ∇ ∇c", position=[0,0])
    context: Dict[str, Any] = {}
    print(execute_qpu_opcode("⊕", ["a", "b"], test_cell, context))
    print(execute_qpu_opcode("↔", ["x", "y"], test_cell, context))
    print(execute_qpu_opcode("∇", [], test_cell, context))   # numeric float
    print(execute_qpu_opcode("∇c", ["data"], test_cell, context))  # preserved compress behavior
    print(get_qpu_metrics())