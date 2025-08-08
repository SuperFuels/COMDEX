# -*- coding: utf-8 -*-
# backend/modules/sqi/kg_bridge.py
"""
Safe bridge to KnowledgeGraphWriter. If KG writer isn’t present, we no-op gracefully.
"""
from __future__ import annotations
from typing import Dict, Any, List
from backend.modules.sqi.drift_types import DriftReport, DriftGap

def _to_kg_nodes(report: DriftReport) -> List[Dict[str, Any]]:
    nodes = []
    for g in report.gaps:
        nodes.append({
            "type": "sqi_drift_gap",
            "container_id": report.container_id,
            "name": g.name,
            "reason": g.reason,
            "missing": g.missing,
            "weight": g.weight,
            "status": report.status,
        })
    # summary node
    nodes.append({
        "type": "sqi_drift_summary",
        "container_id": report.container_id,
        "total_weight": report.total_weight,
        "status": report.status,
        "meta": report.meta,
    })
    return nodes

def write_report_to_kg(report: DriftReport) -> Dict[str, Any]:
    try:
        from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
    except Exception:
        # fallback: return structure for logging
        return {"written": 0, "reason": "KG writer not available", "payload": _to_kg_nodes(report)}

    nodes = _to_kg_nodes(report)
    kg = KnowledgeGraphWriter()
    written = 0
    for n in nodes:
        try:
            kg.write_node(n)   # assumes simple write_node(dict) API
            written += 1
        except Exception:
            pass
    return {"written": written, "payload_count": len(nodes)}