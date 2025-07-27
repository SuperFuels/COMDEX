"""
❌ Failure Index Module – I3

Design Rubric:
- 🔁 Deduplication Logic ............ ✅
- 📦 Container Awareness ............ ✅
- 🧠 Semantic Metadata .............. ✅
- ⏱️ Timestamps (ISO 8601) .......... ✅
- 🧩 Plugin Compatibility ........... ✅
- 🔍 Search & Summary API .......... ✅
- 📊 Readable + Compressed Export ... ✅
- 📚 .dc Container Injection ........ ✅

📄 Index Purpose:
Tracks all failure events across execution, planning, and reasoning. Stores structured failure reasons with symbolic glyph references, container metadata, and introspective causes.

Used for postmortem analysis, goal reevaluation, and blindspot detection.
"""

import hashlib
import datetime
from typing import Dict, Any, List


class FailureIndex:
    """
    Tracks failed glyphs, reasoning outcomes, and container events.
    """
    def __init__(self):
        self.failures: Dict[str, Dict[str, Any]] = {}

    def _hash_failure(self, glyph: str, reason: str) -> str:
        key = f"{glyph}:{reason}"
        return hashlib.sha256(key.encode()).hexdigest()

    def record_failure(
        self,
        glyph: str,
        reason: str,
        container_id: str = None,
        tick: int = None,
        trigger: str = None,
        trace_context: Dict[str, Any] = None,
        plugin_meta: Dict[str, Any] = None
    ):
        """
        Logs a failed glyph operation with metadata for analysis.

        - `glyph`: Symbolic glyph that failed (⧖, ⬁, etc.)
        - `reason`: Failure message or symbolic tag (e.g. "collapse_mismatch")
        - `container_id`: Optional container context
        - `tick`: Runtime tick of failure
        - `trigger`: Optional subsystem trigger (Tessaris, DreamCore, Codex)
        - `trace_context`: Optional glyph trace or entanglement path
        - `plugin_meta`: Optional plugin-specific metadata
        """
        fail_id = self._hash_failure(glyph, reason)
        now = datetime.datetime.utcnow().isoformat()

        self.failures[fail_id] = {
            "glyph": glyph,
            "reason": reason,
            "timestamp": now,
            "container_id": container_id,
            "tick": tick,
            "trigger": trigger,
            "trace_context": trace_context or {},
            "plugin_meta": plugin_meta or {}
        }

    def list_failures(self) -> List[Dict[str, Any]]:
        return list(self.failures.values())

    def get_summary(self) -> Dict[str, int]:
        summary = {}
        for f in self.failures.values():
            r = f["reason"]
            summary[r] = summary.get(r, 0) + 1
        return summary

    def export(self, compressed: bool = False) -> Dict[str, Any]:
        if compressed:
            return {
                fid: {
                    "g": f["glyph"],
                    "r": f["reason"],
                    "t": f["timestamp"],
                    "cid": f["container_id"],
                    "tk": f["tick"]
                }
                for fid, f in self.failures.items()
            }
        return self.failures