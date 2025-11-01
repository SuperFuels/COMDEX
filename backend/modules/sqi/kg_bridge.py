from __future__ import annotations
# ============================================================
# 📁 backend/modules/sqi/kg_bridge.py
# ============================================================
"""
KnowledgeGraphBridge
====================

Bridges SQI drift reports and coherence metrics into the Tessaris Knowledge Graph.
Provides a safe write layer that no-ops gracefully if the KG writer is unavailable.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
from backend.modules.sqi.drift_types import DriftReport, DriftGap

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

# -------------------------------------------------------------------------
#  Knowledge Graph Bridge
# -------------------------------------------------------------------------
class KnowledgeGraphBridge:
    """
    Safe, stateful bridge from SQI / QQC modules to the Knowledge Graph writer.
    Provides consistent logging, error recovery, and optional buffering.
    """

    def __init__(self):
        self.buffer: List[Dict[str, Any]] = []
        self.total_written = 0
        logger.info("[KnowledgeGraphBridge] Initialized KG bridge.")

    # ──────────────────────────────────────────────
    #  Event Injection Interface
    # ──────────────────────────────────────────────
    def inject_trace_event(self, data: Dict[str, Any]) -> None:
        """
        Accepts a symbolic or beam trace event and writes it to the KG if available.
        Falls back to internal buffer if the KG writer is unavailable.
        """
        try:
            from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
            kg_writer.write_node(data)
            self.total_written += 1
            logger.debug(f"[KnowledgeGraphBridge] Wrote event -> {data.get('type', 'unknown')}")
        except Exception as e:
            self.buffer.append(data)
            logger.debug(f"[KnowledgeGraphBridge] Buffered event (KG unavailable): {e}")

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

    # ──────────────────────────────────────────────
    #  Drift Report Writer
    # ──────────────────────────────────────────────
    def write_drift_report(self, report: Any) -> Dict[str, Any]:
        """
        High-level entrypoint for writing a full SQI DriftReport.
        """
        try:
            from backend.modules.knowledge_graph.kg_writer_singleton import write_report_to_kg
            result = write_report_to_kg(report)
        except Exception as e:
            logger.warning(f"[KnowledgeGraphBridge] write_report_to_kg failed: {e}")
            result = {"written": 0}

        self.total_written += result.get("written", 0)
        if result.get("written", 0):
            logger.info(f"[KnowledgeGraphBridge] ↳ {result['written']} nodes written for {getattr(report, 'container_id', '?')}")
        else:
            logger.warning("[KnowledgeGraphBridge] No nodes written (fallback or KG offline).")
        return result

    # ──────────────────────────────────────────────
    #  Unified Trace Export (Symbolic + Photonic + Holographic)
    # ──────────────────────────────────────────────
    @staticmethod
    def export_all_traces(symbolic_trace=None, photonic_trace=None, holographic_trace=None, container_id=None):
        """
        Export a unified trace bundle for symbolic, photonic, and holographic layers.
        Falls back to local JSON export if KG is not available.
        """
        unified = {
            "container_id": container_id,
            "symbolic": symbolic_trace,
            "photonic": photonic_trace,
            "holographic": holographic_trace,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Try writing to live KG writer if available
            from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
            kg_writer.write_node({
                "type": "UnifiedTrace",
                "data": unified
            })
            logger.info(f"[📡 KGBridge] Unified trace injected into KG -> {container_id}")
            return unified
        except Exception as e:
            # Fallback to local export
            path = f"./exports/kg/{container_id}_unified_trace.json"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(unified, f, indent=2)
            logger.warning(f"[📁 KGBridge] KG unavailable, exported locally -> {path} ({e})")
            return unified