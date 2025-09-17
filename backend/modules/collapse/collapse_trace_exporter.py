# backend/modules/collapse/collapse_trace_exporter.py

"""
📦 Collapse Trace Exporter
--------------------------------------
Exports HyperdriveEngine or SQI runtime state snapshots into `.dc.json`
format for symbolic replay, GHX visualization, or entanglement analysis.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from backend.models.fork import Fork

TRACE_LOG_PATH = os.getenv("TRACE_LOG_PATH", "./logs/collapse_traces.jsonl")

from backend.modules.glyphwave.core.beam_state import (
    filter_beams_by_collapse_status,
    group_beams_by_tick,
    extract_unique_ticks,
)

# Core modules
from backend.modules.creative.innovation_scorer import compute_innovation_score
from backend.modules.creative.innovation_memory_tracker import log_event as log_innovation_event
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

# Optional simplifier
try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
    _SIMPLIFIER = CodexLangRewriter()
except Exception:
    _SIMPLIFIER = None

# Optional ethics filter
try:
    from backend.modules.soul.soullaw_symbol_gating import evaluate_soullaw_violations
except Exception:
    evaluate_soullaw_violations = None

# Setup export path
EXPORT_DIR = Path("data/collapse_traces")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# --- Collapse Event Logging ------------------------------------------------
from sqlalchemy.orm import Session
from backend.database import get_db  # ✅ Correct import
from backend.models.fork import Fork

def get_forks_by_wave_id(wave_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve symbolic wave forks associated with a given wave_id from the DB.
    """
    db: Session = next(get_db())
    forks = (
        db.query(Fork)
        .filter(Fork.parent_wave_id == wave_id)
        .all()
    )
    return [
        {
            "id": fork.id,
            "sqi_score": fork.sqi_score,
        }
        for fork in forks
    ]

def log_event_to_disk(event: Dict[str, Any], filename: str = "beam_collapse_log.jsonl"):
    """
    Append a collapse/beam event to the disk log.
    """
    filepath = EXPORT_DIR / filename
    with filepath.open("a", encoding="utf-8") as f:
        json.dump(event, f)
        f.write("\n")

def log_beam_collapse(wave_id: str, collapse_state: Dict[str, Any]):
    """
    Logs the collapse of a wave, including any forks it merged from.
    """
    forks = get_forks_by_wave_id(wave_id)
    event = {
        "wave_id": wave_id,
        "collapsed": True,
        "collapse_state": collapse_state,
        "timestamp": time.time(),
        "merged_forks": [
            {
                "fork_id": fork["id"],
                "collapsed_from": wave_id,
                "sqi_score": fork.get("sqi_score"),
                "merge_flag": True,
            }
            for fork in forks
        ]
    }
    log_event_to_disk(event)

def export_collapse_trace_from_sheet(
    cells: List[GlyphCell],
    out_path: str = "collapse_trace.dc.json",
    container_id: str = "sheet_runtime",
    metadata: dict = {}
):
    """
    Exports the current state of an AtomSheet (list of GlyphCells) into a .dc.json trace container.
    """
    if not cells:
        print("[⚠️] No cells to export.")
        return

    print(f"[📦] Exporting collapse trace for {len(cells)} cells → {out_path}")

    snapshot = {
        "type": "DimensionContainer",
        "id": container_id,
        "format": "dc.json",
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata,
        "cells": [],
        "traces": [],
    }

    for cell in cells:
        snapshot["cells"].append({
            "id": cell.id,
            "logic": cell.logic,
            "position": cell.position,
            "emotion": cell.emotion,
            "prediction": cell.prediction,
            "sqi": cell.sqi_score,
            "result": cell.result,
            "validated": cell.validated,
            "linked": cell.linked_cells,
            "nested": cell.nested_logic,
            # 🧬 Mutation tracking fields
            "mutation_type": getattr(cell, "mutation_type", None),
            "mutation_parent_id": getattr(cell, "mutation_parent_id", None),
            "mutation_score": getattr(cell, "mutation_score", None),
            "mutation_timestamp": getattr(cell, "mutation_timestamp", datetime.utcnow().isoformat() + "Z"),
        })

        if cell.trace:
            snapshot["traces"].append({
                "cell_id": cell.id,
                "events": cell.trace,
            })

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"[✅] Collapse trace exported to {out_path}")

def _safe_filename(stem: str) -> str:
    """Sanitize a filename stem (no path separators)."""
    return "".join(c for c in stem if c.isalnum() or c in ("-", "_")) or "trace"

def _normalize_entanglement_links(glyphs: List[Dict[str, Any]]) -> None:
    """
    Ensure entangled links are symmetrical (↔) across all glyphs.
    For example, if g1 is entangled with g2, then g2 must also list g1.
    """
    id_map = {g.get("id"): g for g in glyphs if "id" in g}
    for g in glyphs:
        ent = g.get("entangled")
        if not isinstance(ent, list):
            continue
        for eid in ent:
            target = id_map.get(eid)
            if target:
                t_ent = target.setdefault("entangled", [])
                if g["id"] not in t_ent:
                    t_ent.append(g["id"])
    # Optional cleanup: deduplicate and sort
    for g in glyphs:
        ent = g.get("entangled")
        if isinstance(ent, list):
            g["entangled"] = sorted(set(ent))

def _simplify_codexlang(glyphs: List[Dict[str, Any]]) -> None:
    """Attempt to simplify CodexLang entries using CodexLangRewriter."""
    if not _SIMPLIFIER:
        return
    for glyph in glyphs:
        lang = glyph.get("codexlang")
        if isinstance(lang, str) and lang.strip():
            try:
                simplified = _SIMPLIFIER.simplify(lang)
                if simplified and simplified != lang:
                    glyph["codexlang_simplified"] = simplified
            except Exception:
                continue

def _apply_soullaw_gate(glyphs: List[Dict[str, Any]]) -> None:
    """Apply SoulLaw evaluation to symbolic glyphs."""
    if evaluate_soullaw_violations:
        try:
            status_map = evaluate_soullaw_violations(glyphs)
            for g in glyphs:
                gid = g.get("id")
                if gid and gid in status_map:
                    g["soullaw_status"] = status_map[gid]
        except Exception as e:
            print(f"[⚠️ SoulLaw evaluation skipped]: {e}")

def _compute_codex_summary(glyphs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Produce a summary block of glyph types, entanglement density, etc.
    """
    summary = {
        "total": len(glyphs),
        "entangled": 0,
        "types": {},
    }
    for g in glyphs:
        if isinstance(g.get("entangled"), list) and g["entangled"]:
            summary["entangled"] += 1
        typ = g.get("type") or "unknown"
        summary["types"][typ] = summary["types"].get(typ, 0) + 1
    return summary

def export_collapse_trace(
    state: Dict[str, Any],
    filename: str | None = None,
    glyph_trace: List[Dict[str, Any]] | None = None,
) -> str:
    """
    Export a collapse trace to disk in `.dc.json` format.

    Args:
        state: Engine or SQI state dictionary.
        filename: Optional filename stem or full name. If omitted, a timestamped
                  name is generated. If a stem is provided without extension,
                  `.dc.json` is appended.
        glyph_trace: Optional glyph trace list (prediction/log metadata).

    Returns:
        Full path to the saved file (str).
    """
    glyphs = state.get("glyphs")
    if isinstance(glyphs, list):
        _normalize_entanglement_links(glyphs)
        _simplify_codexlang(glyphs)
        _apply_soullaw_gate(glyphs)
        state["codex_summary"] = _compute_codex_summary(glyphs)
    
        # 🧠 Inject innovation scores into glyphs
        try:
            for g in glyphs:
                if "innovation_score" not in g:
                    score = compute_innovation_score(g)
                    if score is not None:
                        g["innovation_score"] = round(score, 4)
        except Exception as e:
            print(f"[⚠️ Innovation scoring skipped]: {e}")

    if filename is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"collapse_trace_{ts}.dc.json"
    else:
        name = _safe_filename(Path(filename).stem)
        if not str(filename).endswith(".dc.json"):
            filename = f"{name}.dc.json"
        else:
            filename = f"{name}.dc.json"  # normalize stem anyway

    filepath = EXPORT_DIR / filename

    # 🔮 Inject glyph trace if provided
    if glyph_trace:
        # 🌟 Inject scoring into suggested rewrites
        try:
            from backend.modules.codex.codex_metric import CodexMetrics
            from backend.modules.goal_engine import GoalEngine

            active_goals = GoalEngine.active_goals()

            for entry in glyph_trace:
                rewrite = entry.get("suggested_rewrite")
                if isinstance(rewrite, dict):
                    goal_score = CodexMetrics.score_alignment(rewrite, active_goals)
                    success_prob = CodexMetrics.estimate_rewrite_success(rewrite)

                    rewrite["goal_match_score"] = round(goal_score, 3)
                    rewrite["rewrite_success_prob"] = round(success_prob, 3)

        except Exception as e:
            print(f"[⚠️ Rewrite scoring skipped]: {e}")

        state["glyph_trace"] = glyph_trace  # Reassign updated trace

    if "wave_state" in locals() or "wave_state" in globals():
        qwave = getattr(wave_state, "qwave", None)
        if qwave:
            state["qwave"] = {
                "beams": qwave.get("beams"),
                "modulation_strategy": qwave.get("modulation_strategy"),
                "multiverse_frame": qwave.get("multiverse_frame"),
            }
    
        # 🧠 Log exported collapse into innovation memory
    try:
        log_innovation_event({
            "source": "collapse_trace_exporter",
            "label": state.get("label") or filename,
            "glyphs": glyphs if isinstance(glyphs, list) else [],
            "timestamp": datetime.utcnow().isoformat(),
            "codex_summary": state.get("codex_summary"),
        })
        print("🧠 Collapse trace innovation logged to memory tracker.")
    except Exception as e:
        print(f"[⚠️ Innovation memory logging failed]: {e}")

    # 📂 Write to disk
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

    print(f"📂 Collapse trace exported: {filepath}")
    return str(filepath)

def load_collapse_trace(filename: str) -> Dict[str, Any]:
    """
    Load a previously exported collapse trace from disk.

    Args:
        filename: Filename or full path to `.dc.json` trace.

    Returns:
        Loaded trace state (dict).
    """
    p = Path(filename)
    if not p.exists():
        p = EXPORT_DIR / filename
    if not p.exists():
        raise FileNotFoundError(f"Collapse trace not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        trace = json.load(f)

    print(f"📂 Collapse trace loaded: {p}")
    return trace

# --- Listing helpers -------------------------------------------------------

def iter_collapse_trace_files(limit: int = 50) -> List[Tuple[str, float]]:
    """
    Return up to `limit` most recent collapse trace files (path, mtime).
    """
    if not EXPORT_DIR.exists():
        return []
    files = sorted(
        EXPORT_DIR.glob("*.dc.json"),
        key=lambda q: q.stat().st_mtime,
        reverse=True,
    )[: max(0, int(limit))]
    return [(str(p), p.stat().st_mtime) for p in files]

def get_recent_collapse_traces(
    path: str = TRACE_LOG_PATH,
    show_collapsed: bool = True,
    limit: int = 50,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Loads collapse trace data from the given path (default to TRACE_LOG_PATH),
    applies optional filtering and returns grouped beams for replay.

    Args:
        path (str): Path to .dc.json trace file.
        show_collapsed (bool): Whether to include collapsed branches.
        limit (int): Max entries to return (if streaming format later).
        include_metadata (bool): If true, include path/timestamp.

    Returns:
        Dict: {
            "ticks": [tick ints],
            "grouped_beams": {tick: [beams]},
            "all_beams": [beams],
            "path": str (if include_metadata),
            "timestamp": float (if include_metadata)
        }
    """
    if not os.path.exists(path):
        return {"ticks": [], "grouped_beams": {}, "all_beams": []}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e), "ticks": [], "grouped_beams": {}, "all_beams": []}

    # Apply collapse status filter
    filtered = filter_beams_by_collapse_status(data, show_collapsed=show_collapsed)
    grouped = group_beams_by_tick(filtered)
    ticks = extract_unique_ticks(filtered)

    result = {
        "ticks": ticks,
        "grouped_beams": grouped,
        "all_beams": filtered,
    }

    if include_metadata:
        result["path"] = path
        result["timestamp"] = os.path.getmtime(path)

    return result

import os

TRACE_LOG_PATH_JSONL = "/backend/data/logs/collapse_trace_log.jsonl"
TRACE_LOG_PATH_JSON = "/backend/data/logs/collapse_trace_log.dc.json"

def get_recent_collapse_traces(limit: int = 100) -> List[Dict]:
    """
    Return the most recent collapse traces from either .jsonl or .dc.json file.
    Prioritizes .dc.json for full structured reads.
    """
    traces = []

    # Prefer full .dc.json for structured access
    if os.path.exists(TRACE_LOG_PATH_JSON):
        try:
            with open(TRACE_LOG_PATH_JSON, "r") as f:
                all_traces = json.load(f)
                traces = all_traces[-limit:]
        except Exception as e:
            print(f"[CollapseTrace] Error reading JSON: {e}")

    # Fallback: streaming .jsonl if .dc.json missing
    elif os.path.exists(TRACE_LOG_PATH_JSONL):
        try:
            with open(TRACE_LOG_PATH_JSONL, "r") as f:
                lines = f.readlines()[-limit:]
                traces = [json.loads(line) for line in lines if line.strip()]
        except Exception as e:
            print(f"[CollapseTrace] Error reading JSONL: {e}")

    else:
        print("[CollapseTrace] No trace files found.")

    return traces

def derive_beam_style(collapse_state: str) -> str:
    """
    Map collapse state to frontend beam style.
    """
    if collapse_state == "live":
        return "glow"  # 🟢 glowing beam
    elif collapse_state == "collapsed":
        return "faded"  # 🔴 faded
    elif collapse_state == "predicted":
        return "dashed"  # 🟠 dashed
    elif collapse_state == "contradicted":
        return "broken"  # ⚫ broken
    else:
        return "default"

__all__ = [
    "export_collapse_trace",
    "load_collapse_trace",
    "iter_collapse_trace_files",
    "get_recent_collapse_traces",
    "export_collapse_trace_from_sheet",  
]
