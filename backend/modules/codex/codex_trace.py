# 📁 backend/modules/codex/codex_trace.py

import time
import json
from typing import List, Dict, Optional

class CodexTrace:
    def __init__(self):
        self.entries: List[Dict] = []

    def record(self, glyph: str, context: dict, result: str, source: str = "benchmark"):
        self.entries.append({
            "timestamp": time.time(),
            "glyph": glyph,
            "context": context,
            "result": result,
            "source": source
        })

    def get_trace(self) -> List[Dict]:
        return self.entries

    def clear(self):
        self.entries = []

    def to_json(self) -> str:
        return json.dumps(self.entries, indent=2)

    def get_latest_trace(self, container_id: Optional[str] = None) -> Optional[Dict]:
        for entry in reversed(self.entries):
            ctx = entry.get("context", {})
            if container_id is None or ctx.get("container_id") == container_id:
                return {
                    "ghx_id": ctx.get("ghx_id"),
                    "path": ctx.get("collapse_trace"),
                    "container_id": ctx.get("container_id"),
                    "timestamp": entry.get("timestamp"),
                    "glyph": entry.get("glyph"),
                    "result": entry.get("result"),
                    "source": entry.get("source"),
                }
        return None

    # ✅ Prediction trace injection for .dc.json containers
    @staticmethod
    def inject_prediction_trace(
        container_id: str,
        glyph_id: str,
        beam_source: str,
        predicted_label: str,
        confidence: float,
        entropy: float,
        logic_score: float,
        all_candidates: list
    ):
        trace_entry = {
            "type": "glyph",
            "glyph": predicted_label,
            "action": "predict",
            "source": beam_source,
            "timestamp": time.time(),
            "cost": logic_score,
            "predicted": True,
            "beamSource": beam_source,
            "confidence": confidence,
            "entropy": entropy,
            "detail": {
                "glyph_id": glyph_id,
                "candidates": all_candidates,
            },
            "context": container_id,
        }
        _global_trace.entries.append(trace_entry)

    # ✅ Rewrite trace for executed Codex rewrites
    @staticmethod
    def inject_rewrite_trace(container_id: str, glyph_id: str, original: str, rewritten: str, reason: str):
        _global_trace.entries.append({
            "type": "glyph",
            "glyph": rewritten,
            "action": "rewrite",
            "timestamp": time.time(),
            "source": "rewrite_executor",
            "context": container_id,
            "detail": {
                "glyph_id": glyph_id,
                "original": original,
                "rewritten": rewritten,
                "reason": reason,
            },
        })

    # ✅ Contradiction trace
    @staticmethod
    def inject_contradiction_trace(container_id: str, glyph_id: str, contradiction_info: dict):
        _global_trace.entries.append({
            "type": "glyph",
            "glyph": glyph_id,
            "action": "contradiction",
            "timestamp": time.time(),
            "source": "prediction_engine",
            "context": container_id,
            "detail": contradiction_info,
        })

    # ✅ Simplification suggestion trace
    @staticmethod
    def inject_simplification_trace(container_id: str, glyph_id: str, suggestions: List[str]):
        _global_trace.entries.append({
            "type": "glyph",
            "glyph": glyph_id,
            "action": "simplify",
            "timestamp": time.time(),
            "source": "prediction_engine",
            "context": container_id,
            "detail": {
                "suggestions": suggestions
            }
        })

    # ✅ Replay trace for step-wise replays
    @staticmethod
    def inject_replay_trace(container_id: str, glyph_id: str, step: str, notes: Optional[str] = None):
        _global_trace.entries.append({
            "type": "glyph",
            "glyph": glyph_id,
            "action": "replay_step",
            "timestamp": time.time(),
            "source": "codex_executor",
            "context": container_id,
            "detail": {
                "step": step,
                "notes": notes
            }
        })


# ✅ Global singleton
_global_trace = CodexTrace()

def log_codex_trace(glyph: str, context: dict, result: str, source: str = "benchmark"):
    _global_trace.record(glyph, context, result, source)

def get_codex_trace():
    return _global_trace.get_trace()

def get_latest_trace(container_id: Optional[str] = None):
    return _global_trace.get_latest_trace(container_id)

# ✅ Execution path wrapper for GHXEncoder
def trace_glyph_execution_path(glyph_id: str) -> Dict:
    matching = [e for e in _global_trace.get_trace() if e.get("glyph") == glyph_id]
    return {
        "glyph_id": glyph_id,
        "steps": matching,
        "count": len(matching),
        "latest": matching[-1] if matching else None
    }