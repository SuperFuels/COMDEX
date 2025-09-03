# backend/modules/collapse/collapse_trace_exporter.py

"""
📦 Collapse Trace Exporter
--------------------------------------
Exports HyperdriveEngine or SQI runtime state snapshots into `.dc.json`
format for symbolic replay, GHX visualization, or entanglement analysis.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

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

EXPORT_DIR = Path("data/collapse_traces")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

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

def get_recent_collapse_traces(limit: int = 50, load: bool = True) -> List[Dict[str, Any]]:
    """
    Return recent collapse traces. If load=True, parse JSON and include path/mtime.
    Otherwise returns metadata entries only.
    """
    results: List[Dict[str, Any]] = []
    for path, mtime in iter_collapse_trace_files(limit=limit):
        if load:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("path", path)
                    data.setdefault("timestamp", mtime)
                    results.append(data)
                else:
                    results.append({"path": path, "timestamp": mtime, "data": data})
            except Exception:
                continue
        else:
            results.append({"path": path, "timestamp": mtime})
    return results

__all__ = [
    "export_collapse_trace",
    "load_collapse_trace",
    "iter_collapse_trace_files",
    "get_recent_collapse_traces",
]
