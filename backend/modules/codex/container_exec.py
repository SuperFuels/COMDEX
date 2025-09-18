# ===============================
# 📁 backend/modules/codex/container_exec.py
# ===============================
from typing import Any, Dict, List, Optional

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


def _as_token(op: str) -> Dict[str, Any]:
    return {"type": "operator", "value": op}


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
    """
    # Index cells
    idx = {c.id: c for c in (cells or [])}
    results: List[Dict[str, Any]] = []
    ok, err = 0, 0

    for i, item in enumerate(batch or []):
        cid = item.get("cell_id")
        op = item.get("op")
        stage = item.get("stage") or "container"
        args = item.get("args")

        if not cid or not op or cid not in idx:
            err += 1
            results.append({
                "idx": i, "cell_id": cid, "op": op,
                "ok": False, "error": "invalid cell/op"
            })
            continue

        cell = idx[cid]
        try:
            # Ensure cell sees this context
            context["cell"] = cell
            setattr(cell, "_ctx", context)

            # If no explicit args, pass a single opcode token (like per-token execution path)
            exec_args = args if isinstance(args, list) else [_as_token(op)]

            res = execute_qpu_opcode(op, exec_args, cell, context)

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
            }
            cell.wave_beams.append(beam)

            results.append({
                "idx": i, "cell_id": cid, "op": op,
                "ok": True, "result": res, "beam_id": beam["beam_id"]
            })
            ok += 1
        except Exception as e:
            err += 1
            record_trace(cid, f"[QFC Container Exec Error] {e}")
            results.append({
                "idx": i, "cell_id": cid, "op": op,
                "ok": False, "error": str(e)
            })

    summary = {
        "container_id": container_id,
        "sheet_run_id": context.get("sheet_run_id"),
        "ok": ok,
        "error": err,
        "total": ok + err,
        "results": results[:50],  # cap for telemetry payload
    }
    record_trace("sheet", f"[Phase10/QFC] container batch: ok={ok} error={err} total={ok+err}")
    return summary