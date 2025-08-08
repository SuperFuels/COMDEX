# -*- coding: utf-8 -*-
# backend/modules/sqi/kg_drift.py
from __future__ import annotations
import json
from typing import Any, Dict, List

from backend.modules.sqi.sqi_math_adapter import compute_drift
from backend.modules.knowledge_graph.knowledge_graph_writer import kg_writer

# optional suggestions
try:
    from backend.modules.sqi.sqi_harmonics import suggest_harmonics
except Exception:
    suggest_harmonics = None  # graceful fallback

def _augment_with_suggestions(container: Dict[str, Any], report: Dict[str, Any]) -> None:
    """Mutates the drift report dict in-place to attach lemma suggestions (if available)."""
    if not suggest_harmonics:
        return
    for gap in report.get("gaps", []):
        if gap.get("reason") == "missing_dependencies":
            missing = gap.get("missing", []) or []
            suggs: List[Dict[str, Any]] = []
            for m in missing:
                cands = suggest_harmonics(container, m, top_k=3)
                suggs.append({
                    "missing": m,
                    "candidates": [{"name": n, "score": round(s, 3)} for (n, s) in cands]
                })
            gap["suggestions"] = suggs

def push_drift_report_to_kg(container_path: str, suggest: bool = False) -> Dict[str, Any]:
    """
    Compute drift for a .dc container file and inject a summarized drift glyph + gap entries
    into the Knowledge Graph. Returns the report as a dict.
    """
    with open(container_path, "r", encoding="utf-8") as f:
        container = json.load(f)

    # compute
    rep_obj = compute_drift(container)  # returns a DriftReport dataclass
    report = {
        "container_id": rep_obj.container_id,
        "total_weight": rep_obj.total_weight,
        "status": rep_obj.status,
        "gaps": [g.__dict__ for g in rep_obj.gaps],
        "meta": rep_obj.meta,
    }

    # optional suggestions
    if suggest:
        _augment_with_suggestions(container, report)

    # write top-level drift glyph
    kg_writer.inject_glyph(
        content=f"DriftReport[{report['container_id']}] weight={report['total_weight']} status={report['status']}",
        glyph_type="drift_report",
        metadata={"report": report, "container_path": container_path},
        plugin="SQI-Drift",
        agent_id="sqi",
        tags=["sqi","drift","analysis"],
    )

    # write each gap as its own glyph (nice for search/filter)
    for gap in report["gaps"]:
        kg_writer.inject_glyph(
            content=f"DriftGap[{gap.get('name','?')}] reason={gap.get('reason')} weight={gap.get('weight')}",
            glyph_type="drift_gap",
            metadata={"gap": gap, "container_id": report["container_id"]},
            plugin="SQI-Drift",
            agent_id="sqi",
            tags=["sqi","drift","gap"],
        )

    return report