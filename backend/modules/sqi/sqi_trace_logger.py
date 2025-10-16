# backend/modules/sqi/sqi_trace_logger.py
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SQITraceLogger:
    """
    Trace logger for SQI events.
    - Keeps original static log_trace() for compatibility
    - Adds event list tracking + log_collapse() for CodexExecutor
    """

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    # ✅ Legacy static method (unchanged)
    @staticmethod
    def log_trace(engine, message: str) -> None:
        """
        Legacy trace logging — writes to logger only.
        """
        logger.info(f"[SQITrace] {message}")

    # ✅ New generic event logger
    def log_event(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Store event in memory + also write to logger.
        """
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "kind": kind,
            "payload": payload or {},
        }
        self.events.append(entry)
        logger.info(f"[SQITrace:{kind}] {payload or {}}")

    # ✅ New API used by CodexExecutor
    def log_collapse(self, glyph: str, cost: float, entangled: bool = False) -> None:
        """
        Record a QGlyph collapse event with cost + entanglement flag.
        """
        self.log_event("collapse", {
            "glyph": glyph,
            "cost": float(cost),
            "entangled": bool(entangled),
        })

    # Utility
    def recent(self, n: int = 25) -> List[Dict[str, Any]]:
        """
        Return last N events.
        """
        return self.events[-n:]

    def reset(self) -> None:
        """
        Clear all stored events.
        """
        self.events.clear()

    def start_session(self, session_id: str) -> None:
        """Compatibility shim for QQC boot sequence."""
        self.log_event("session_start", {"session_id": session_id})


    def end_session(self, session_id: str) -> None:
        """
        Compatibility shim for QQC shutdown.
        Marks the end of a trace session.
        """
        self.log_event("session_end", {"session_id": session_id})
        print(f"[SQITraceLogger] Session {session_id} ended.")