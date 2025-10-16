# -*- coding: utf-8 -*-
# ============================================================
# 📁 backend/modules/sqi/kg_bridge.py
# ============================================================

"""
KnowledgeGraphBridge
====================

Bridges SQI drift reports and coherence metrics into the Tessaris Knowledge Graph.
Provides a safe write layer that no-ops gracefully if the KG writer is unavailable.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List

from backend.modules.sqi.drift_types import DriftReport, DriftGap

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────
def _to_kg_nodes(report: DriftReport) -> List[Dict[str, Any]]:
    """Convert DriftReport into a list of Knowledge Graph node dicts."""
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
    """Functional API (legacy): write drift report nodes into KG."""
    try:
        from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
    except Exception:
        return {"written": 0, "reason": "KG writer not available", "payload": _to_kg_nodes(report)}

    nodes = _to_kg_nodes(report)
    written = 0
    for n in nodes:
        try:
            kg_writer.write_node(n)
            written += 1
        except Exception as e:
            logger.warning(f"[KG Bridge] Node write failed: {e}")
    return {"written": written, "payload_count": len(nodes)}


# ──────────────────────────────────────────────
#  Class Interface (for QQC)
# ──────────────────────────────────────────────
class KnowledgeGraphBridge:
    """
    Safe, stateful bridge from SQI modules to the Knowledge Graph writer.
    Provides consistent logging, error recovery, and optional buffering.
    """

    def __init__(self):
        self.buffer: List[Dict[str, Any]] = []
        self.total_written = 0
        logger.info("[KnowledgeGraphBridge] Initialized KG bridge.")

    def inject_trace_event(self, data: Dict[str, Any]) -> None:
        """
        Accepts a symbolic or beam trace event and writes it to the KG if available.
        """
        try:
            from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
            kg_writer.write_node(data)
            self.total_written += 1
            logger.debug(f"[KnowledgeGraphBridge] Wrote event → {data.get('type', 'unknown')}")
        except Exception:
            # fall back to buffer
            self.buffer.append(data)
            logger.debug("[KnowledgeGraphBridge] Buffered event (KG unavailable).")

    def flush_buffer(self) -> int:
        """
        Attempt to write all buffered events.
        Returns number of successfully written nodes.
        """
        try:
            from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
        except Exception:
            logger.warning("[KnowledgeGraphBridge] KG writer still unavailable; buffer retained.")
            return 0

        success = 0
        for item in list(self.buffer):
            try:
                kg_writer.write_node(item)
                success += 1
                self.buffer.remove(item)
            except Exception:
                pass
        self.total_written += success
        logger.info(f"[KnowledgeGraphBridge] Flushed {success} buffered nodes.")
        return success

    def write_drift_report(self, report: DriftReport) -> Dict[str, Any]:
        """
        High-level entrypoint for writing a full SQI DriftReport.
        """
        result = write_report_to_kg(report)
        self.total_written += result.get("written", 0)
        if result.get("written", 0):
            logger.info(f"[KnowledgeGraphBridge] ↳ {result['written']} nodes written for {report.container_id}")
        else:
            logger.warning("[KnowledgeGraphBridge] No nodes written (fallback or KG offline).")
        return result