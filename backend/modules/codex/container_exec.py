# ===============================
# 📁 backend/modules/codex/container_exec.py
# ===============================
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Defensive GlyphCell (test-friendly)
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

# Lazy tokenizer
try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
except Exception:
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]

from backend.modules.codex.hardware.symbolic_qpu_isa import execute_qpu_opcode
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms

# Optional jsonschema for batch validation (no hard dependency)
try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None  # type: ignore

# -----------------------------
# Helpers
# -----------------------------
def _as_token(op: str) -> Dict[str, Any]:
    return {"type": "operator", "value": op}

def _sqi_lazy(cell: GlyphCell) -> float:
    """
    Try preferred scorer; fall back to existing value or 1.0 without crashing.
    """
    try:
        # preferred scorer used elsewhere in the codebase
        from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
        return float(score_sqi(cell))
    except Exception:
        try:
            return float(getattr(cell, "sqi_score", 1.0) or 1.0)
        except Exception:
            return 1.0

# Optional schema for validating incoming batch items
BATCH_SCHEMA = {
    "type": "object",
    "required": ["cell_id", "op"],
    "properties": {
        "cell_id": {"type": "string"},
        "op": {"type": "string"},
        "args": {"type": "array"},
        "stage": {"type": "string"},
    },
    "additionalProperties": True,
}

def _validate_batch_safe(batch: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
    """
    Validate a batch with jsonschema if available. Never hard-fail:
    returns (#invalid_items, errors).
    """
    if jsonschema is None:
        return (0, [])
    invalid = 0
    errors: List[str] = []
    for i, item in enumerate(batch or []):
        try:
            jsonschema.validate(instance=item, schema=BATCH_SCHEMA)  # type: ignore
        except Exception as e:
            invalid += 1
            errors.append(f"item[{i}]: {e}")
    return (invalid, errors)

# -----------------------------
# Main API
# -----------------------------
def execute_qfc_container_beams(
    container_id: Optional[str],
    cells: List[GlyphCell],
    batch: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a QFC-provided batch of ops at *container* scope.

    batch item shape (tolerant):
      {
        "cell_id": "c1",           # required
        "op": "↔",                 # required (symbolic opcode)
        "args": ["x","y"] | null,  # optional; if absent, a token for `op` is passed
        "stage": "container"       # optional label
      }

    Extras (world-class enhancements):
      * Dynamic SQI refresh per cell after op execution.
      * Optional jsonschema validation of batch items (no hard dependency).
      * Lightweight metrics in `context["qpu_metrics"]`.
      * Opt-in parallelization via context["parallel_container_exec"] (default False)
        and context["container_exec_workers"] (default 4). Sequential remains default.
    """
    # Ensure metrics dict
    qpu_metrics = context.setdefault("qpu_metrics", {})
    # Validate batch (never hard-fail)
    invalid_count, invalid_errors = _validate_batch_safe(batch or [])
    if invalid_count:
        record_trace("qfc", f"[ContainerExec] batch validation issues: {invalid_count} invalid; {invalid_errors[:3]}")

    # Index cells
    idx = {c.id: c for c in (cells or [])}
    results: List[Dict[str, Any]] = []

    # Parallel settings (opt-in)
    use_parallel = bool(context.get("parallel_container_exec", False))
    max_workers = int(context.get("container_exec_workers", 4) or 4)

    def _exec_one(i: int, item: Dict[str, Any]) -> Dict[str, Any]:
        cid = item.get("cell_id")
        op = item.get("op")
        stage = item.get("stage") or "container"
        args = item.get("args")

        if not cid or not op or cid not in idx:
            qpu_metrics[f"{cid}:{op}:{i}"] = {"error": "invalid cell/op"}
            return {"idx": i, "cell_id": cid, "op": op, "ok": False, "error": "invalid cell/op"}

        cell = idx[cid]
        try:
            # Ensure cell sees this context
            context["cell"] = cell
            setattr(cell, "_ctx", context)

            # If no explicit args, pass a single opcode token (like per-token execution path)
            exec_args = args if isinstance(args, list) else [_as_token(op)]

            t0 = now_utc_ms()
            res = execute_qpu_opcode(op, exec_args, cell, context)
            t1 = now_utc_ms()

            # Dynamic SQI refresh (non-fatal)
            try:
                cell.sqi_score = _sqi_lazy(cell)
            except Exception:
                pass

            # Emit a container-exec beam for lineage/visualizers
            if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
                cell.wave_beams = []
            beam = {
                "beam_id": f"beam_{cell.id}_container_{now_utc_ms()}",
                "source": "qfc_container_exec",
                "stage": stage,           # 'container' by default
                "token": op,
                "timestamp": now_utc_iso(),
                "result": res,
                "context_ref": {
                    "container_id": container_id,
                    "sheet_run_id": context.get("sheet_run_id")
                },
                "sqi_after": float(getattr(cell, "sqi_score", 1.0) or 1.0),
            }
            cell.wave_beams.append(beam)

            # Update metrics
            qpu_metrics[f"{cid}:{op}:{i}"] = {
                "time_ms": max(0, int(t1) - int(t0)),
                "beam_id": beam["beam_id"],
            }

            return {"idx": i, "cell_id": cid, "op": op, "ok": True, "result": res, "beam_id": beam["beam_id"]}
        except Exception as e:
            record_trace(cid, f"[QFC Container Exec Error] {e}")
            qpu_metrics[f"{cid}:{op}:{i}"] = {"error": str(e)}
            return {"idx": i, "cell_id": cid, "op": op, "ok": False, "error": str(e)}

    # Execute (sequential by default; optional parallel)
    if not use_parallel:
        for i, item in enumerate(batch or []):
            results.append(_exec_one(i, item))
    else:
        # Parallel execution - keep modest defaults; caller controls workers
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            fut_map = {ex.submit(_exec_one, i, item): i for i, item in enumerate(batch or [])}
            for fut in as_completed(fut_map):
                results.append(fut.result())

    # Summarize
    ok = sum(1 for r in results if r.get("ok"))
    err = sum(1 for r in results if not r.get("ok"))

    summary = {
        "container_id": container_id,
        "sheet_run_id": context.get("sheet_run_id"),
        "ok": ok,
        "error": err,
        "total": ok + err,
        "results": results[:50],  # cap for telemetry payload
        "metrics": qpu_metrics,   # lightweight timing/error markers
        "validation_warnings": invalid_errors[:10] if invalid_errors else [],
    }
    record_trace("sheet", f"[Phase10/QFC] container batch: ok={ok} error={err} total={ok+err} parallel={use_parallel}")
    return summary

# ============================================================
# 📦 DimensionContainerExec - High-level QFC container runtime adapter
# ============================================================

class DimensionContainerExec:
    """
    Provides class-based access to the container beam execution subsystem.
    Wraps the procedural API (`execute_qfc_container_beams`) so higher-level
    orchestrators (like QQC or CodexFabric) can call it via an instance.

    Example:
        dce = DimensionContainerExec()
        result = dce.run(container_id, cells, batch, context)
    """

    def __init__(self):
        self.last_summary: Optional[Dict[str, Any]] = None
        self.executor_pool = None
        print("[DimensionContainerExec] Initialized container runtime executor.")

    def run(
        self,
        container_id: Optional[str],
        cells: List[Any],
        batch: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a batch at container level (Codex/QFC integrated path).
        Wraps execute_qfc_container_beams() with safety and logging.
        """
        from backend.modules.codex.container_exec import execute_qfc_container_beams

        ctx = context or {}
        try:
            summary = execute_qfc_container_beams(container_id, cells, batch, ctx)
            self.last_summary = summary
            if summary.get("error", 0):
                print(f"[DimensionContainerExec] ⚠️ {summary['error']} errors for container {container_id}")
            else:
                print(f"[DimensionContainerExec] ✅ Executed container {container_id} with {summary['ok']} ops.")
            return summary
        except Exception as e:
            print(f"[DimensionContainerExec] ❌ Failed to execute container {container_id}: {e}")
            return {"status": "error", "error": str(e)}

    def summarize(self) -> Dict[str, Any]:
        """
        Return the last execution summary if available.
        """
        return self.last_summary or {"status": "no_runs"}

    def clear_summary(self):
        """Reset internal state."""
        self.last_summary = None

    def extract_state(self):
        """Return lightweight container state snapshot for PortalManager."""
        return {"status": "noop", "message": "extract_state() not implemented yet"}