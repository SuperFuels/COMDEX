# ===============================
# 🌙 backend/modules/codex/dreams_4d.py
# Phase 9: Dream Projection & Timeline Replay
# - Speculative beam generation ("dreams")
# - Timeline scrub/replay payload
# - SQI-guided pruning
# - Deterministic EID fallback (sheet_run_id + normalized tokens)
# ===============================

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from hashlib import blake2s

# ---- Lazy/defensive imports to avoid circulars ----
try:
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
except Exception:  # very defensive for tests
    class GlyphCell:  # type: ignore
        def __init__(self, id: str, logic: str = "", position=None):
            self.id = id
            self.logic = logic
            self.wave_beams = []
            self.prediction_forks = []
            self.sqi_score = 1.0
            self._ctx = {}

try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
except Exception:
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]

try:
    from backend.modules.patterns.pattern_trace_engine import record_trace
except Exception:
    def record_trace(k, msg):  # noqa: E306
        print(f"[Trace {k}] {msg}")

# Time helpers (Phase 8+ compliant)
try:
    from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms
except Exception:
    from datetime import datetime, timezone
    def now_utc_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
    def now_utc_ms() -> int:
        return int(datetime.now(timezone.utc).timestamp() * 1000)

# ------------------------------------------------------------------------
# Config knobs
# ------------------------------------------------------------------------
@dataclass
class DreamConfig:
    k_variants: int = 3          # how many speculative variants per cell
    min_sqi_keep: float = 0.60   # prune dreams below this SQI
    tag_entanglement: bool = True
    stage_name: str = "dream"    # 'dream' stage for Phase 9 beams

# ------------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------------
def _compute_eid_for_cell(context: Dict[str, Any], cell: GlyphCell) -> str:
    """
    Deterministic EID per sheet_run_id + normalized tokens.
    Guarantees an EID even if none were produced earlier.
    """
    sheet_run_id = context.get("sheet_run_id", "run")
    logic = (getattr(cell, "logic", "") or "")
    tokens = tokenize_symbol_text_to_glyphs(logic)
    sig = " ".join(t.get("value", "") for t in tokens)
    digest = blake2s(f"{sheet_run_id}::{sig}".encode("utf-8"), digest_size=8).hexdigest()
    return f"eid::{sheet_run_id}::{digest}"

def _entanglements_for_cell(cell: GlyphCell, context: Dict[str, Any]) -> List[str]:
    """Collect any EIDs the cell participates in (from context map or beams)."""
    eids = set()
    # sweep entanglement map
    for eid, members in (context.get("entanglements_map", {}) or {}).items():
        if getattr(cell, "id", None) in members:
            eids.add(eid)
    # sweep existing beams
    for b in (getattr(cell, "wave_beams", []) or []):
        for e in (b.get("entanglement_ids") or []):
            if e:
                eids.add(e)
    return sorted(eids)

def _score_sqi_lazy(cell: GlyphCell) -> float:
    """Lazy SQI import; fallback to current sqi_score."""
    try:
        from backend.modules.codex.codex_virtual_qpu import _score_sqi  # lazy to dodge circulars
        return float(_score_sqi(cell))
    except Exception:
        return float(getattr(cell, "sqi_score", 1.0) or 1.0)

def _mk_beam_id(cell_id: str, stage: str) -> str:
    return f"beam_{cell_id}_{stage}_{now_utc_ms()}"

def _dream_payload_variants(tokens: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """
    Super lightweight speculative variants from token stream.
    Intent: produce plausible symbolic next-steps, not correctness.
    """
    sig = [t.get("value", "") for t in tokens]
    variants: List[Dict[str, Any]] = []
    base = " ".join(sig)

    # Pattern-ish tweaks
    recipes = [
        lambda s: s + " ✦",                   # add milestone
        lambda s: s.replace("↔", "→ ↔"),      # insert trigger before eq
        lambda s: "∇ " + s,                   # prepend numeric probe
        lambda s: s + " ⟲",                   # mutate end
        lambda s: s.replace("→", "→ ✦"),      # trigger then milestone
    ]
    for i in range(max(1, int(k))):
        f = recipes[i % len(recipes)]
        variants.append({"prediction": f(base), "variant": i})
    return variants

# ------------------------------------------------------------------------
# Core Phase 9 API
# ------------------------------------------------------------------------
def project_dreams_for_cell(
    cell: GlyphCell,
    context: Dict[str, Any],
    cfg: Optional[DreamConfig] = None
) -> List[Dict[str, Any]]:
    """
    Generate speculative 'dream' beams for a single cell.
    Always tags with at least one EID (existing or deterministic fallback).
    """
    cfg = cfg or DreamConfig()
    tokens = tokenize_symbol_text_to_glyphs(getattr(cell, "logic", "") or "")
    variants = _dream_payload_variants(tokens, cfg.k_variants)
    eids = _entanglements_for_cell(cell, context) if cfg.tag_entanglement else []

    # ensure we have at least one EID for linkage/visualizers
    if cfg.tag_entanglement and not eids:
        try:
            eids = [_compute_eid_for_cell(context, cell)]
        except Exception:
            eids = []

    dreams: List[Dict[str, Any]] = []
    for v in variants:
        beam = {
            "beam_id": _mk_beam_id(cell.id, cfg.stage_name),
            "source": "phase9_dreams",
            "stage": cfg.stage_name,  # <-- Phase 9 stage tag
            "token": {"type": "operator", "value": "∴"},  # decorative dream marker
            "payload": v,
            "timestamp": now_utc_iso(),
            "entanglement_ids": eids,
            "eid": (eids[0] if eids else None),  # convenience field
            "sqi": float(getattr(cell, "sqi_score", 1.0) or 1.0),
            "state": "active",
            "cell_id": cell.id,
        }
        # attach to cell
        if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
            cell.wave_beams = []
        cell.wave_beams.append(beam)
        dreams.append(beam)

    record_trace(cell.id, f"[Phase9] projected {len(dreams)} dream(s)")
    return dreams

def prune_dreams_by_sqi(
    cell: GlyphCell,
    min_sqi: float = 0.60,
    stage_name: str = "dream"
) -> None:
    """
    Mark low-score dreams as pruned (non-destructive).
    """
    beams = getattr(cell, "wave_beams", []) or []
    sqi = _score_sqi_lazy(cell)
    if sqi < float(min_sqi):
        for b in beams:
            if b.get("stage") == stage_name:
                b["state"] = "pruned"
        if beams:
            record_trace(cell.id, f"[Phase9] pruned dreams sqi={sqi:.2f} < {float(min_sqi):.2f}")

def build_timeline_snapshot(cells: List[GlyphCell], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten cell beams into a time-sorted stream (for scrub/replay).
    """
    timeline: List[Dict[str, Any]] = []
    for c in cells:
        for b in (getattr(c, "wave_beams", []) or []):
            eid = (b.get("entanglement_ids") or [None])[0]
            timeline.append({
                "cell_id": c.id,
                "beam_id": b.get("beam_id"),
                "stage": b.get("stage"),
                "token": b.get("token"),
                "eid": eid,
                "timestamp": b.get("timestamp"),
                "state": b.get("state", "active"),
            })
    # stable sort by timestamp then beam_id
    timeline.sort(key=lambda x: (str(x.get("timestamp") or ""), str(x.get("beam_id") or "")))
    record_trace("sheet", f"[Phase9] timeline size={len(timeline)}")
    return timeline

def phase9_run(
    cells: List[GlyphCell],
    context: Dict[str, Any],
    *,
    k_variants: int = 3,
    min_sqi_keep: float = 0.60,
    stage_name: str = "dream"
) -> Dict[str, Any]:
    """
    End-to-end Phase 9 pass:
      1) project dreams
      2) prune by SQI
      3) build timeline snapshot
    Returns payloads for broadcasts.
    """
    cfg = DreamConfig(k_variants=k_variants, min_sqi_keep=min_sqi_keep, stage_name=stage_name)

    # 1) dreams
    per_cell: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells:
        per_cell[c.id] = project_dreams_for_cell(c, context, cfg)

    # 2) prune
    for c in cells:
        prune_dreams_by_sqi(c, min_sqi=min_sqi_keep, stage_name=stage_name)

    # 3) timeline
    timeline = build_timeline_snapshot(cells, context)

    return {
        "dreams": per_cell,
        "timeline": timeline
    }