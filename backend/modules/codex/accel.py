# ===============================
# 📁 backend/modules/codex/accel.py
# ===============================
from typing import Any, Dict, List

# -----------------------------
# Optional vector backends (guardrails)
# -----------------------------
_HAS_NUMPY = False
_HAS_NUMEXPR = False
_HAS_TORCH = False

try:  # NumPy (preferred)
    import numpy as _np  # type: ignore
    _HAS_NUMPY = True
except Exception:
    _np = None  # type: ignore

try:  # numexpr (optional micro-ops on NumPy arrays)
    import numexpr as _ne  # type: ignore
    _HAS_NUMEXPR = True
except Exception:
    _ne = None  # type: ignore

try:  # PyTorch (fallback vector backend)
    import torch as _torch  # type: ignore
    _HAS_TORCH = True
except Exception:
    _torch = None  # type: ignore

# -----------------------------
# Defensive GlyphCell
# -----------------------------
try:
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
except Exception:
    class GlyphCell:  # type: ignore
        def __init__(self, id: str, logic: str = "", position=None):
            self.id = id
            self.logic = logic
            self.wave_beams = []
            self.prediction_forks = []
            self.sqi_score = 1.0
            self._ctx = {}

# -----------------------------
# Lazy tokenizer
# -----------------------------
try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
except Exception:
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]

from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms

# ISA (reuse scalar ops safely)
from backend.modules.codex.hardware.symbolic_qpu_isa import (
    execute_qpu_opcode,
    _op_nabla,  # numeric probe suitable for quantization tests
)

# ============================================================
# Precision helpers
# ============================================================
def _sanitize_mode(mode: str) -> str:
    m = (mode or "").lower()
    if m in ("fp4", "fp8", "int8", "fp32", "none"):
        return m
    return "fp8"

def _precision_for_op(op: str, context: Dict[str, Any], default_mode: str) -> str:
    """
    Per-opcode precision gates honoring profiler/context:
      1) context["phase10_precisions"] -> {op: "fp4"|"fp8"|"int8"|"fp32"}
      2) context["precision_profile"]:
         - either {op: "fp8"} mapping, or
         - {"fp4": [...ops], "fp8": [...], "int8":[...], "fp32":[...]}
      3) fallback to default_mode
    """
    # explicit per-op override
    per_op = (context.get("phase10_precisions") or {})
    if isinstance(per_op, dict):
        m = per_op.get(op)
        if isinstance(m, str):
            return _sanitize_mode(m)

    # profiler-style profile
    prof = context.get("precision_profile") or {}
    if isinstance(prof, dict):
        # direct mapping
        m = prof.get(op)
        if isinstance(m, str):
            return _sanitize_mode(m)
        # buckets
        for bucket in ("fp4", "fp8", "int8", "fp32"):
            ops = prof.get(bucket)
            if isinstance(ops, (list, tuple, set)) and op in ops:
                return bucket

    return _sanitize_mode(default_mode)

# ============================================================
# Quantization emulation
# ============================================================
def _quantize_to(mode: str, x: float) -> float:
    m = _sanitize_mode(mode)
    if m in ("none", "fp32"):
        return float(x)
    if m == "int8":
        v = max(-127, min(127, int(round(float(x) * 127))))
        return v / 127.0
    if m == "fp8":
        return float(round(float(x) * 4) / 4)  # 2 fractional bits (toy)
    if m == "fp4":
        return float(round(float(x)))           # 1-bit-ish toy
    return float(x)

def _quantize_array(mode: str, arr: List[float]) -> List[float]:
    """Vector path (NumPy/Torch) with safe scalar fallback."""
    m = _sanitize_mode(mode)
    # NumPy fast path
    if _HAS_NUMPY:
        a = _np.asarray(arr, dtype=_np.float32)
        if m in ("none", "fp32"):
            q = a
        elif m == "int8":
            q = _np.clip(_np.rint(a * 127), -127, 127) / 127.0
        elif m == "fp8":
            q = _np.rint(a * 4) / 4.0
        elif m == "fp4":
            # Use numexpr if available for the rint to avoid temporary arrays
            if _HAS_NUMEXPR:
                q = _ne.evaluate("round(a)")  # type: ignore
            else:
                q = _np.rint(a)
        else:
            q = a
        return q.astype(_np.float32).tolist()

    # Torch fallback
    if _HAS_TORCH:
        ta = _torch.tensor(arr, dtype=_torch.float32)
        if m in ("none", "fp32"):
            tq = ta
        elif m == "int8":
            tq = _torch.clamp(_torch.round(ta * 127), -127, 127) / 127.0
        elif m == "fp8":
            tq = _torch.round(ta * 4) / 4.0
        elif m == "fp4":
            tq = _torch.round(ta)
        else:
            tq = ta
        return tq.tolist()

    # Scalar fallback (always available)
    return [_quantize_to(m, float(v)) for v in arr]

# ============================================================
# Batch consecutive identical ops
# ============================================================
def _build_batches(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    batches: List[Dict[str, Any]] = []
    cur = None
    for t in tokens:
        if t.get("type") != "operator":
            continue
        op = t.get("value")
        if cur and cur["op"] == op:
            cur["tokens"].append(t)
        else:
            if cur:
                batches.append(cur)
            cur = {"op": op, "tokens": [t]}
    if cur:
        batches.append(cur)
    return batches

# ============================================================
# Vectorize a single cell (Phase 10)
# ============================================================
def vectorize_cell(cell: GlyphCell, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    tokens = tokenize_symbol_text_to_glyphs(getattr(cell, "logic", "") or "")
    batches = _build_batches(tokens)
    default_mode = _sanitize_mode(str(context.get("phase10_precision", "fp8") or "fp8"))

    # Note which backends are live (for telemetry/debug)
    backends = []
    if _HAS_NUMPY:
        backends.append("numpy")
    if _HAS_NUMEXPR:
        backends.append("numexpr")
    if _HAS_TORCH:
        backends.append("torch")
    if not backends:
        backends.append("scalar")

    summaries: List[Dict[str, Any]] = []
    for b in batches:
        op = b["op"]
        mode_for_batch = _precision_for_op(op, context, default_mode)

        results = []
        qerrors: List[float] = []

        if op == "∇":
            # Numeric probe: generate base values for each token in batch
            bases = [float(_op_nabla([], {"cell": cell})) for _ in b["tokens"]]

            # Vector quantize with guardrails
            quant = _quantize_array(mode_for_batch, bases)

            # Error stats (vector if possible)
            if _HAS_NUMPY:
                be = _np.abs(_np.asarray(bases, dtype=_np.float32) -
                             _np.asarray(quant, dtype=_np.float32))
                qerr_mean = float(be.mean())
            elif _HAS_TORCH:
                tb = _torch.tensor(bases, dtype=_torch.float32)
                tq = _torch.tensor(quant, dtype=_torch.float32)
                qerr_mean = float(_torch.mean(_torch.abs(tb - tq)).item())
            else:
                qerr_mean = sum(abs(a - q) for a, q in zip(bases, quant)) / max(1, len(bases))

            results = list(quant)
            qerrors = []  # we track mean only
        else:
            # Non-numeric ops: execute scalar path safely
            for t in b["tokens"]:
                try:
                    res = execute_qpu_opcode(op, [t], cell, context)
                except Exception as e:
                    res = [f"[Error {op}: {e}]"]
                results.append(res)
            qerr_mean = 0.0  # not applicable

        beam = {
            "beam_id": f"beam_{cell.id}_vector_{now_utc_ms()}",
            "source": "accel",
            "stage": "vector",
            "token": op,
            "timestamp": now_utc_iso(),
            "precision": mode_for_batch,
            "backend": backends[0],  # primary backend used
            "batch_size": len(b["tokens"]),
            "result_sample": results[:3],
            "quant_error_mean": qerr_mean,
        }
        if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
            cell.wave_beams = []
        cell.wave_beams.append(beam)

        summaries.append({
            "cell_id": cell.id,
            "op": op,
            "batch_size": beam["batch_size"],
            "precision": mode_for_batch,
            "backend": beam["backend"],
            "quant_error_mean": beam["quant_error_mean"],
            "beam_id": beam["beam_id"],
        })

    record_trace(cell.id, f"[Phase10] vectorized {len(summaries)} batch(es)")
    return summaries

# ============================================================
# Sheet-level entry point
# ============================================================
def phase10_accelerate_sheet(cells: List[GlyphCell], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Phase 10 vectorization pass on all cells.
    Guardrails:
      • If NumPy/numexpr/torch are missing, we transparently fall back to scalar.
      • Per-opcode precision selected via _precision_for_op(...).
    """
    summary: Dict[str, Any] = {}
    total = 0
    for c in cells:
        try:
            batches = vectorize_cell(c, context)
        except Exception as e:
            record_trace(getattr(c, "id", "sheet"), f"[Phase10 error] {e}")
            batches = []
        summary[c.id] = batches
        total += len(batches)

    env = {
        "numpy": _HAS_NUMPY,
        "numexpr": _HAS_NUMEXPR,
        "torch": _HAS_TORCH,
        "fallback": not (_HAS_NUMPY or _HAS_TORCH),
    }
    return {"batches": summary, "total_batches": total, "env": env}