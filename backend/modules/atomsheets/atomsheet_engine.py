# ===============================
# 📁 backend/modules/atomsheets/atomsheet_engine.py
# ===============================
from __future__ import annotations
from typing import Any, Dict, List, Union, Optional
import json
import os
from pathlib import Path

from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms

# Models / Registry
from .models import AtomSheet, GlyphCell
from .registry import register_sheet

# Tokenizer (defensive)
try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
except Exception:
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]

# QPU (sheet execution) + lazy SQI
from backend.modules.codex.codex_virtual_qpu import CodexVirtualQPU
def _score_sqi_lazy(cell: GlyphCell) -> float:
    """
    Lazy SQI: use CodexVirtualQPU._score_sqi (which already lazy-imports the real scorer),
    falling back to the current .sqi_score on failure.
    """
    try:
        from backend.modules.codex.codex_virtual_qpu import _score_sqi as _impl
        return float(_impl(cell))
    except Exception:
        try:
            return float(getattr(cell, "sqi_score", 1.0) or 1.0)
        except Exception:
            return 1.0

# ─────────────────────────────────────────────────────────────────────────────
# Optional JSON Schema validation (no hard dependency)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None  # type: ignore

def _load_local_schema() -> Optional[Dict[str, Any]]:
    """
    Try to load a local schema file next to this module:
      backend/modules/atomsheets/sqs.schema.json
    Returns dict or None if missing/unreadable.
    """
    try:
        here = Path(__file__).resolve().parent
        schema_path = here / "sqs.schema.json"
        if schema_path.exists():
            with open(schema_path, "r") as f:
                return json.load(f)
    except Exception as e:
        record_trace("atomsheet", f"[Schema Warn] Failed to load schema: {e}")
    return None

def _validate_sqs_schema(data: Dict[str, Any]) -> None:
    """
    Validate the SQS payload against the JSON schema if jsonschema + schema are available.
    Otherwise, no-op with a trace for awareness.
    """
    if jsonschema is None:
        record_trace("atomsheet", "[Schema] jsonschema not installed — skipping validation")
        return
    schema = _load_local_schema()
    if not schema:
        record_trace("atomsheet", "[Schema] sqs.schema.json not found — skipping validation")
        return
    try:
        jsonschema.validate(instance=data, schema=schema)  # type: ignore
    except Exception as e:
        # raise as ValueError to keep callers’ expectations simple
        raise ValueError(f"SQS schema validation failed: {e}") from e

# ─────────────────────────────────────────────────────────────────────────────
# Public API (module-level functions kept for compatibility)
# ─────────────────────────────────────────────────────────────────────────────
def load_sqs(src: Union[str, Dict[str, Any]]) -> AtomSheet:
    """
    Load an AtomSheet from a .sqs.json dict or file path.

    Minimal expected format:
      {
        "id": "sheet_id",
        "title": "...",
        "dims": [x,y,z,w],
        "cells": [
          {"id":"c1","logic":"⊕ ∇ ↔","position":[0,0,0,0],"emotion":"neutral","meta":{...}},
          ...
        ],
        "meta": {...}
      }
    """
    try:
        if isinstance(src, str):
            with open(src, "r") as f:
                data = json.load(f)
        else:
            data = dict(src)

        # Optional schema validation (no-op if unavailable)
        _validate_sqs_schema(data)

        sid = data.get("id") or f"sheet_{now_utc_ms()}"
        title = data.get("title", "")
        dims = data.get("dims") or [1, 1, 1, 1]
        meta = data.get("meta") or {}

        cells: Dict[str, GlyphCell] = {}
        for c in data.get("cells", []):
            gc = GlyphCell(
                id=c.get("id"),
                logic=c.get("logic", "") or "",
                position=c.get("position") or [0, 0, 0, 0],
                emotion=c.get("emotion", "neutral")
            )
            # stash any meta
            for k, v in (c.get("meta") or {}).items():
                try:
                    setattr(gc, k, v)
                except Exception:
                    pass
            cells[gc.id] = gc

        sheet = AtomSheet(id=sid, title=title, dims=dims, meta=meta, cells=cells)
        register_sheet(sheet)
        record_trace("atomsheet", f"[Load] id={sheet.id} cells={len(sheet.cells)} dims={sheet.dims}")
        return sheet
    except ValueError:
        # schema failure already wrapped; bubble up
        raise
    except Exception as e:
        record_trace("atomsheet", f"[Load Error] {e}")
        raise

async def execute_sheet(sheet: AtomSheet, context: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    Execute all cells through the Codex QPU (Phase 7/8/9/10 stack).
    Returns: {cell_id: results}
    """
    qpu = CodexVirtualQPU()
    # Carry sheet context
    ctx = dict(context or {})
    ctx.setdefault("sheet_run_id", ctx.get("sheet_run_id"))
    ctx["sheet_cells"] = list(sheet.cells.values())

    try:
        results = await qpu.execute_sheet(list(sheet.cells.values()), ctx)
    except Exception as e:
        record_trace("atomsheet", f"[Execute Error] {e}")
        raise

    # Refresh SQI (defensive) and append a sheet-level beam for lineage
    try:
        for c in sheet.cells.values():
            try:
                c.sqi_score = _score_sqi_lazy(c)
            except Exception:
                pass
    finally:
        sheet_beam = {
            "beam_id": f"beam_{sheet.id}_sheet_{now_utc_ms()}",
            "source": "atomsheet_execute",
            "stage": "collapse",
            "token": "∑",
            "result": {"cells": list(results.keys()), "counts": {k: len(v) for k, v in results.items()}},
            "timestamp": now_utc_iso(),
        }
        # append to each cell for visibility in GHX/QFC
        for c in sheet.cells.values():
            if not hasattr(c, "wave_beams") or c.wave_beams is None:
                c.wave_beams = []
            c.wave_beams.append(sheet_beam)

    record_trace("atomsheet", f"[Execute] sheet={sheet.id} cells={len(sheet.cells)}")
    return results

def to_dc_json(sheet: AtomSheet, path: Optional[str] = None) -> Dict[str, Any]:
    """
    Export a replayable snapshot (.dc.json-like) of the current AtomSheet.
    """
    try:
        payload = {
            "id": sheet.id,
            "title": sheet.title,
            "type": "atomsheet_snapshot",
            "dims": sheet.dims,
            "meta": sheet.meta,
            "timestamp": now_utc_iso(),
            "cells": [
                {
                    "id": c.id,
                    "logic": c.logic,
                    "emotion": getattr(c, "emotion", "neutral"),
                    "position": getattr(c, "position", [0, 0, 0, 0]),
                    "prediction": getattr(c, "prediction", ""),
                    "prediction_forks": list(getattr(c, "prediction_forks", []) or []),
                    "sqi_score": float(getattr(c, "sqi_score", 1.0) or 1.0),
                    "wave_beams": list(getattr(c, "wave_beams", []) or []),
                }
                for c in sheet.cells.values()
            ],
        }

        if path:
            out_path = Path(path)
            if out_path.parent and not out_path.parent.exists():
                out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(payload, f, indent=2)

        record_trace("atomsheet", f"[Export] id={sheet.id} cells={len(sheet.cells)}")
        return payload
    except Exception as e:
        record_trace("atomsheet", f"[Export Error] {e}")
        raise