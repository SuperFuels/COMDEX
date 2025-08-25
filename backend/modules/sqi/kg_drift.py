# -*- coding: utf-8 -*-
# backend/modules/sqi/kg_drift.py
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from backend.modules.sqi.sqi_math_adapter import compute_drift

# Optional suggestions (graceful fallback if module not present)
try:
    from backend.modules.sqi.sqi_harmonics import suggest_harmonics
except Exception:
    suggest_harmonics = None  # type: ignore[assignment]

def _get_kg_writer():
    """
    Lazy import to avoid circular import chains.
    Returns the shared KnowledgeGraphWriter instance (kg_writer).
    """
    from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
    kg_writer = get_kg_writer()
    return kg_writer

def _augment_with_suggestions(container: Dict[str, Any], report: Dict[str, Any]) -> None:
    """
    Mutates the drift report dict in-place to attach lemma suggestions (if available).
    """
    if not suggest_harmonics:
        return

    for gap in report.get("gaps", []) or []:
        if gap.get("reason") == "missing_dependencies":
            missing = gap.get("missing", []) or []
            suggs: List[Dict[str, Any]] = []
            for m in missing:
                try:
                    cands = suggest_harmonics(container, m, top_k=3)  # type: ignore[misc]
                except Exception:
                    cands = []
                suggs.append({
                    "missing": m,
                    "candidates": [{"name": n, "score": round(s, 3)} for (n, s) in cands]
                })
            gap["suggestions"] = suggs

def push_drift_report_to_kg(
    container_path: str,
    suggest: bool = False,
    writer: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Compute drift for a .dc container file and inject:
      1) A summarized drift glyph
      2) Individual gap glyphs
    into the Knowledge Graph.

    Args:
        container_path: Path to the .dc container JSON.
        suggest: If True, augment the report with harmonic suggestions (if available).
        writer: Optional explicit KnowledgeGraphWriter-like object with .inject_glyph().
                If not provided, a shared writer is lazily imported to avoid circular deps.

    Returns:
        The drift report as a dict.
    """
    with open(container_path, "r", encoding="utf-8") as f:
        container = json.load(f)

    # Compute drift (returns a DriftReport dataclass from sqi_math_adapter)
    rep_obj = compute_drift(container)
    report: Dict[str, Any] = {
        "container_id": rep_obj.container_id,
        "total_weight": rep_obj.total_weight,
        "status": rep_obj.status,
        "gaps": [g.__dict__ for g in rep_obj.gaps],
        "meta": rep_obj.meta,
    }

    # Optional suggestion enrichment
    if suggest:
        _augment_with_suggestions(container, report)

    # Get KG writer lazily (or use the one injected via arg)
    kgw = writer or _get_kg_writer()

    # 1) Write top-level drift glyph
    kgw.inject_glyph(
        content=f"DriftReport[{report['container_id']}] weight={report['total_weight']} status={report['status']}",
        glyph_type="drift_report",
        metadata={"report": report, "container_path": container_path},
        plugin="SQI-Drift",
        agent_id="sqi",
        tags=["sqi", "drift", "analysis"],
    )

    # 2) Write each gap as its own glyph (useful for search/filter)
    for gap in report["gaps"]:
        kgw.inject_glyph(
            content=f"DriftGap[{gap.get('name','?')}] reason={gap.get('reason')} weight={gap.get('weight')}",
            glyph_type="drift_gap",
            metadata={"gap": gap, "container_id": report["container_id"]},
            plugin="SQI-Drift",
            agent_id="sqi",
            tags=["sqi", "drift", "gap"],
        )

    return report