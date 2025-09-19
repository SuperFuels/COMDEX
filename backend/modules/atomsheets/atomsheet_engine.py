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
from backend.modules.codex.codexlang_evaluator import evaluate_codexlang

# Models / Registry
from .models import AtomSheet, GlyphCell
from .registry import register_sheet

# --- Atom format defaults (canonical) ---
ATOM_EXTS = (".atom", ".sqs.json")  # accept both; prefer `.atom`

def _normalize_atom_path(src: str) -> str:
    """Ensure `.atom` extension if the caller passes a bare name."""
    if any(src.endswith(ext) for ext in ATOM_EXTS):
        return src
    return f"{src}.atom"

# -----------------------------
# Nested expansion helpers (A5)
# -----------------------------
def _get_nested_descriptor(cell: GlyphCell) -> Optional[Dict[str, Any]]:
    # prefer cell.nested if present, else meta.nested
    nested = getattr(cell, "nested", None)
    if isinstance(nested, dict):
        return nested
    meta = getattr(cell, "meta", None)
    if isinstance(meta, dict) and isinstance(meta.get("nested"), dict):
        return meta["nested"]
    return None

def has_nested(cell: GlyphCell) -> bool:
    return _get_nested_descriptor(cell) is not None

def _sheet_from_nested(nested: Dict[str, Any]) -> "AtomSheet":
    ntype = (nested.get("type") or "").lower()
    if ntype == "ref":
        path = nested.get("path")
        if not path:
            raise ValueError("nested.ref requires 'path'")
        return load_atom(path)  # type: ignore[name-defined]
    if ntype == "inline":
        sheet_dict = nested.get("sheet")
        if not isinstance(sheet_dict, dict):
            raise ValueError("nested.inline requires 'sheet' dict")
        return load_atom(sheet_dict)  # type: ignore[name-defined]
    raise ValueError(f"Unknown nested type: {ntype}")

# Prefer new atom schema; fall back to legacy SQS schema if needed
try:
    from backend.schemas.atom.atom_schema import ATOM_SHEET_SCHEMA  # new canonical
except Exception:
    try:
        from backend.schemas.sqs.schema import ATOM_SHEET_SCHEMA  # legacy alias
    except Exception:
        ATOM_SHEET_SCHEMA = {"type": "object"}  # ultra-defensive fallback

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

from typing import Tuple  # at the top with other typing imports

def _compute_e7_metrics(cells: Dict[str, "GlyphCell"]) -> None:
    """
    Compute entropy/novelty/harmony with simple text heuristics.
    - entropy: normalized Shannon entropy of token distribution
    - harmony: avg Jaccard similarity to other cells
    - novelty: 1 - max Jaccard to any other cell
    Values are clamped to [0,1].
    """
    try:
        import math, re
        from collections import Counter

        items = list(cells.values())
        def _toks(s: str) -> list[str]:
            return [t for t in re.split(r"\W+", s or "") if t]

        def _jacc(a: set[str], b: set[str]) -> float:
            u = a | b
            if not u: return 0.0
            return len(a & b) / len(u)

        token_lists = [_toks(getattr(c, "logic", "") or "") for c in items]

        for i, c in enumerate(items):
            toks = token_lists[i]
            # entropy
            if toks:
                cnt = Counter(toks)
                total = sum(cnt.values())
                probs = [n/total for n in cnt.values() if n > 0]
                H = -sum(p * math.log2(p) for p in probs if p > 0)
                Hmax = math.log2(len(cnt)) if len(cnt) > 1 else 1.0
                ent = (H / Hmax) if Hmax > 0 else 0.0
            else:
                ent = 0.0

            # harmony / novelty
            sims = []
            A = set(toks)
            for j, _ in enumerate(items):
                if i == j: continue
                sims.append(_jacc(A, set(token_lists[j])))
            harmony = (sum(sims) / len(sims)) if sims else 0.0
            novelty = 1.0 - (max(sims) if sims else 0.0)

            # clamp + assign
            setattr(c, "entropy", float(max(0.0, min(1.0, ent))))
            setattr(c, "harmony", float(max(0.0, min(1.0, harmony))))
            setattr(c, "novelty", float(max(0.0, min(1.0, novelty))))
    except Exception as e:
        record_trace("atomsheet", f"[E7 Compute Warn] {e}")

def _evaluate_codexlang(text: str, ctx: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Best-effort CodexLang evaluation.
    Tries backend.modules.codex.codexlang_eval.evaluate(text, ctx) → str
    Returns (render, error). If evaluator is missing, returns (text, None).
    """
    try:
        from backend.modules.codex.codexlang_eval import evaluate as codex_eval  # optional
    except Exception:
        codex_eval = None

    if not text:
        return "", None

    if codex_eval is None:
        # graceful fallback: just echo
        return text, None

    try:
        out = codex_eval(text, ctx=ctx)
        return (str(out) if out is not None else ""), None
    except Exception as e:
        return None, str(e)

# --- CodexLang evaluator (optional) -----------------------------------------
def _eval_codexlang_safe(src: str) -> Dict[str, Any]:
    """
    Best-effort CodexLang evaluation. Returns {"ok": bool, "text": str, "error": str|None}
    """
    try:
        from backend.modules.codex.codexlang_evaluator import evaluate_codexlang  # if you have it
    except Exception:
        evaluate_codexlang = None  # type: ignore
    try:
        if not src:
            return {"ok": True, "text": "", "error": None}
        if evaluate_codexlang:
            out = evaluate_codexlang(src)
            # normalize to string for UI preview
            if isinstance(out, (dict, list)):
                import json
                return {"ok": True, "text": json.dumps(out, ensure_ascii=False), "error": None}
            return {"ok": True, "text": str(out), "error": None}
        # fallback: noop just echoes source
        return {"ok": True, "text": src, "error": None}
    except Exception as e:
        return {"ok": False, "text": "", "error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# E7 metrics: entropy / novelty / harmony (no extra deps)
# ─────────────────────────────────────────────────────────────────────────────
from math import log2

def _clamp01(x: float) -> float:
    try:
        if x < 0.0: return 0.0
        if x > 1.0: return 1.0
        return float(x)
    except Exception:
        return 0.0

def _shannon_entropy(text: str) -> float:
    """
    Character-level Shannon entropy normalized to [0,1].
    Uses per-char frequency; empty => 0.
    """
    if not text:
        return 0.0
    counts: Dict[str, int] = {}
    n = 0
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
        n += 1
    # H = - sum p*log2 p
    H = 0.0
    for c in counts.values():
        p = c / n
        H -= p * log2(p)
    # Normalize by max possible entropy log2(alphabet)
    alpha = max(2, len(counts))
    return _clamp01(H / log2(alpha))

def _token_values_for_logic(logic: str) -> List[str]:
    try:
        toks = tokenize_symbol_text_to_glyphs(logic or "")
        vals = []
        for t in toks:
            v = t.get("value")
            # use a safe string repr; avoid None
            vals.append(str(v) if v is not None else "")
        return vals
    except Exception:
        return (logic or "").split()

def _jaccard_similarity(a: List[str], b: List[str]) -> float:
    try:
        sa, sb = set(a), set(b)
        if not sa and not sb:
            return 1.0
        inter = len(sa & sb)
        union = len(sa | sb)
        if union == 0:
            return 0.0
        return _clamp01(inter / union)
    except Exception:
        return 0.0

def _compute_e7_metrics(cells: Dict[str, GlyphCell]) -> None:
    """
    Compute per-cell:
      - entropy: Shannon entropy of token stream (0..1)
      - novelty: 1 - max Jaccard similarity vs others (0..1)
      - harmony: average Jaccard similarity vs others (0..1)
    Stores results on cell.entropy / cell.novelty / cell.harmony
    """
    items = list(cells.values())
    tokenized: Dict[str, List[str]] = {}
    for c in items:
        tokenized[c.id] = _token_values_for_logic(getattr(c, "logic", ""))

    # Precompute similarities
    for i, ci in enumerate(items):
        toks_i = tokenized.get(ci.id, [])
        # entropy from token sequence (concat string is ok)
        ci.entropy = _shannon_entropy(" ".join(toks_i))

        if len(items) == 1:
            ci.novelty = 0.0
            ci.harmony = 1.0
            continue

        sims: List[float] = []
        for j, cj in enumerate(items):
            if i == j:
                continue
            toks_j = tokenized.get(cj.id, [])
            sims.append(_jaccard_similarity(toks_i, toks_j))

        # Novelty = 1 - max_similarity_to_any_other
        max_sim = max(sims) if sims else 0.0
        ci.novelty = _clamp01(1.0 - max_sim)

        # Harmony = average similarity to others
        avg_sim = (sum(sims) / len(sims)) if sims else 1.0
        ci.harmony = _clamp01(avg_sim)

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

# Minimal default schema if nothing else is available
DEFAULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["id", "cells"],
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "dims": {"type": "array"},
        "meta": {"type": "object"},
        "cells": {"type": "array"},
    },
    "additionalProperties": True,
}

def _validate_sqs_schema(data: Dict[str, Any]) -> None:
    """
    Validate the payload against the best-available schema:
      1) Prefer module-imported ATOM_SHEET_SCHEMA (atom/sqs canonical)
      2) Else try local sqs.schema.json next to this module
      3) Else enforce DEFAULT_SCHEMA; if jsonschema is unavailable, do a minimal required-field check

    Raise ValueError on schema issues (callers expect ValueError).
    """
    # 1) Prefer imported ATOM_SHEET_SCHEMA if present
    candidate_schema: Optional[Dict[str, Any]] = None
    try:
        if isinstance(ATOM_SHEET_SCHEMA, dict) and ATOM_SHEET_SCHEMA:
            candidate_schema = ATOM_SHEET_SCHEMA
    except Exception:
        candidate_schema = None

    # 2) Else try local schema file next to this module
    if candidate_schema is None:
        candidate_schema = _load_local_schema()

    # If jsonschema is available, validate with best schema (or DEFAULT_SCHEMA as last resort)
    if jsonschema is not None:
        schema_to_use = candidate_schema or DEFAULT_SCHEMA
        try:
            jsonschema.validate(instance=data, schema=schema_to_use)  # type: ignore[arg-type]
            return
        except Exception as e:
            raise ValueError(f"SQS/ATOM schema validation failed: {e}") from e

    # Fallback: jsonschema not installed → minimal required-field enforcement
    required = DEFAULT_SCHEMA["required"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"SQS/ATOM validation failed: missing required fields {missing}")

    # Passed minimal checks
    record_trace("atomsheet", "[Schema] jsonschema unavailable — passed minimal required-field check")

# ─────────────────────────────────────────────────────────────────────────────
# Public API (module-level functions kept for compatibility)
# ─────────────────────────────────────────────────────────────────────────────
def load_atom(src: Union[str, Dict[str, Any]]) -> AtomSheet:
    """
    Load an AtomSheet from `.atom` (canonical) or legacy `.sqs.json`.
    Structure is identical; only the extension differs.
    """
    # ---- load dict ----
    if isinstance(src, str):
        path = _normalize_atom_path(src)  # use top-level normalizer
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = dict(src)

    # ---- optional validation ----
    # 1) Validate against imported ATOM_SHEET_SCHEMA if jsonschema is available
    try:
        if jsonschema is not None and ATOM_SHEET_SCHEMA:
            jsonschema.validate(instance=data, schema=ATOM_SHEET_SCHEMA)  # type: ignore[arg-type]
    except Exception:
        # ultra-defensive: log, don't hard-fail
        record_trace("atomsheet", "[Load] Schema validation skipped/failed")

    # 2) Also try local sqs.schema.json (no-op if missing)
    try:
        _validate_sqs_schema(data)
    except ValueError:
        # bubble up if the local schema explicitly fails
        raise
    except Exception:
        # ignore other issues (missing file, etc.)
        pass

    # ---- construct model ----
    sid = data.get("id") or f"sheet_{now_utc_ms()}"
    title = data.get("title", "")
    dims = data.get("dims") or [1, 1, 1, 1]
    meta = data.get("meta") or {}

    cells: Dict[str, GlyphCell] = {}
    for idx, c in enumerate(data.get("cells", [])):
        cid = c.get("id") or f"c_{idx}_{now_utc_ms()}"
        gc = GlyphCell(
            id=cid,
            logic=c.get("logic", "") or "",
            position=c.get("position") or [0, 0, 0, 0],
            emotion=c.get("emotion", "neutral"),
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
    record_trace(
        "atomsheet",
        f"[Load] id={sheet.id} ext=.atom (or legacy) cells={len(sheet.cells)} dims={sheet.dims}"
    )
    return sheet

# Backwards-compat alias (old callers keep working)
load_sqs = load_atom

async def execute_sheet(sheet: AtomSheet, context: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    Execute all cells through the Codex QPU (Phase 7/8/9/10 stack).
    Returns: {cell_id: results}

    Adds:
      • Sheet-level collapse beam with counts
      • Defensive SQI refresh per cell
      • (A5) Nested expansion
      • (E7) Compute entropy / novelty / harmony per cell post-execution
      • (B6) CodexLang render for cells marked logic_type=codexlang (or meta.logic_type)
    """
    qpu = CodexVirtualQPU()

    # ---------- Carry/augment context ----------
    ctx = dict(context or {})
    ctx.setdefault("sheet_run_id", ctx.get("sheet_run_id"))
    ctx["sheet_cells"] = list(sheet.cells.values())
    ctx.setdefault("qpu_metrics", {})
    ctx.setdefault("entangled_pairs", [])

    # Guard nested recursion
    max_depth = int(ctx.get("max_nested_depth", 1) or 1)
    depth = int(ctx.get("_nested_depth", 0) or 0)

    # ---------- Execute via QPU (defensive) ----------
    try:
        results = await qpu.execute_sheet(list(sheet.cells.values()), ctx)
        # Tiny per-cell metric (ops count + timestamp)
        for cell_id, res_list in (results or {}).items():
            ctx["qpu_metrics"][cell_id] = {
                "ops": len(res_list) if isinstance(res_list, list) else 0,
                "time": now_utc_ms(),
            }
    except Exception as e:
        record_trace("atomsheet", f"[Execute Error] {e}")
        raise

    # ---------- CodexLang evaluation (server-side preview) ----------
    try:
        for c in sheet.cells.values():
            # decide logic type from either attribute or meta override
            logic_type = getattr(c, "logic_type", None)
            mlt = None
            try:
                mlt = (getattr(c, "meta", {}) or {}).get("logic_type")
            except Exception:
                mlt = None
            logic_type = (mlt or logic_type or "").lower()

            if logic_type == "codexlang":
                render, err = evaluate_codexlang(getattr(c, "logic", "") or "")
                try:
                    setattr(c, "codex_eval", render)
                    setattr(c, "codex_error", err)
                except Exception:
                    pass
    except Exception as e:
        record_trace("atomsheet", f"[CodexLang Eval Warn] {e}")

    # ---------- Refresh SQI defensively ----------
    def _sqi_lazy(cell: GlyphCell) -> float:
        try:
            return float(_score_sqi_lazy(cell))  # type: ignore[name-defined]
        except Exception:
            try:
                from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
                return float(score_sqi(cell))
            except Exception:
                return float(getattr(cell, "sqi_score", 1.0) or 1.0)

    try:
        for c in sheet.cells.values():
            try:
                c.sqi_score = _sqi_lazy(c)
            except Exception:
                pass
    finally:
        # ---------- Sheet-level collapse beam ----------
        sheet_beam = {
            "beam_id": f"beam_{sheet.id}_sheet_{now_utc_ms()}",
            "source": "atomsheet_execute",
            "stage": "collapse",
            "token": "∑",
            "result": {
                "cells": list(results.keys()),
                "counts": {k: len(v) for k, v in results.items()},
            },
            "timestamp": now_utc_iso(),
        }
        for c in sheet.cells.values():
            if not hasattr(c, "wave_beams") or c.wave_beams is None:
                c.wave_beams = []
            c.wave_beams.append(sheet_beam)

    # ---------- (E7) Compute entropy / novelty / harmony ----------
    try:
        _compute_e7_metrics(sheet.cells)
    except Exception as e:
        record_trace("atomsheet", f"[E7 Metrics Warn] {e}")

    # ---------- (B6) CodexLang render (optional) ----------
    try:
        for c in sheet.cells.values():
            logic_type = getattr(c, "logic_type", None)
            meta = getattr(c, "meta", {}) or {}
            lt = (logic_type or meta.get("logic_type") or "").lower()
            if lt == "codexlang":
                render, err = _evaluate_codexlang(getattr(c, "logic", "") or "", ctx)
                setattr(c, "codex_eval", render if render is not None else "")
                if err:
                    setattr(c, "codex_error", err)
    except Exception as e:
        record_trace("atomsheet", f"[CodexLang Eval Warn] {e}")

    # ---------- (A5) Nested expansion (optional) ----------
    if ctx.get("expand_nested") and depth < max_depth:
        child_ctx = dict(ctx)
        child_ctx["_nested_depth"] = depth + 1

        for cell in sheet.cells.values():
            nested = _get_nested_descriptor(cell)
            if not nested:
                continue
            try:
                sub_sheet = _sheet_from_nested(nested)
                sub_results = await execute_sheet(sub_sheet, child_ctx)

                expand_beam = {
                    "beam_id": f"beam_{cell.id}_nested_{now_utc_ms()}",
                    "source": "atomsheet_nested",
                    "stage": "expand",
                    "token": "↘",
                    "result": {
                        "child_sheet_id": sub_sheet.id,
                        "counts": {k: len(v) for k, v in sub_results.items()},
                    },
                    "timestamp": now_utc_iso(),
                    "meta": {
                        "parent_sheet_id": sheet.id,
                        "parent_cell_id": cell.id,
                    },
                }
                if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
                    cell.wave_beams = []
                cell.wave_beams.append(expand_beam)
            except Exception as e:
                record_trace("atomsheet", f"[Nested Expand Warn] {e}")

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
                    "entropy": float(getattr(c, "entropy", 0.0) or 0.0),
                    "novelty": float(getattr(c, "novelty", 0.0) or 0.0),
                    "harmony": float(getattr(c, "harmony", 1.0) or 1.0),
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