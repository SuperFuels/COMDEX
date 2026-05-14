# 📁 backend/modules/codex/codex_trace.py
# Unified Codex Trace + Runtime Integration Layer
# ------------------------------------------------
# Provides global CodexTrace singleton with safe `.log()` interface,
# theorem trace support for Symatics law checks, and MemoryEngine persistence.
# Maintains backward-compatible injection APIs.
# ------------------------------------------------

import time
import json
from typing import List, Dict, Optional, Any


class CodexTrace:
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    # === ✅ Universal Log Hook (Codex + Runtime + Symatics) ===
    def log(self, event: dict):
        """
        Logs a structured Codex or runtime event to the in-memory buffer and,
        if available, to the MemoryEngine via store_memory().

        Event shape (examples):
            {
              "action": "executed" | "predict" | "law_check",
              "source": "glyph_executor" | "codex_executor" | "symatics_dispatcher",
              "glyph": "...",
              "engine": "symatics",
              "operator": "⊕",
              "summary": "5/5 passed",
              "violations": [],
              "context": {...}
            }
        """
        try:
            # Normalize input
            evt = dict(event) if isinstance(event, dict) else {"note": str(event)}
            evt.setdefault("type", "codex_trace")
            evt.setdefault("timestamp", time.time())

            # Default engine/source tagging
            evt.setdefault("engine", "codex")
            evt.setdefault("source", "runtime")

            # Add to in-memory trace
            self.entries.append(evt)

            # Persist to MemoryEngine (lazy import to avoid circular deps)
            try:
                from backend.modules.hexcore.memory_engine import store_memory
                label = f"codex_trace:{evt.get('action', 'event')}"
                store_memory({
                    "label": label,
                    "content": evt,
                })
            except Exception:
                # Skip persistence errors silently
                pass

            # Developer console output
            try:
                print(f"[Trace:Codex] {evt.get('action', 'event')} -> {json.dumps(evt, ensure_ascii=False)}")
            except Exception:
                print("[Trace:Codex] event logged (fallback)")
        except Exception as e:
            print(f"[⚠️ CodexTrace] Failed to log event: {e}")

    # === Core Trace Management ===
    def record(self, glyph: str, context: dict, result: str, source: str = "benchmark"):
        """Legacy API for generic Codex trace recording."""
        self.entries.append({
            "timestamp": time.time(),
            "glyph": glyph,
            "context": context or {},
            "result": result,
            "source": source,
        })

    def get_trace(self) -> List[Dict[str, Any]]:
        return self.entries

    def clear(self):
        self.entries = []

    def to_json(self) -> str:
        return json.dumps(self.entries, indent=2)

    def get_latest_trace(self, container_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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

    # === Specialized Injection APIs (preserved for compatibility) ===
    @staticmethod
    def inject_prediction_trace(
        container_id: str,
        glyph_id: str,
        beam_source: str,
        predicted_label: str,
        confidence: float,
        entropy: float,
        logic_score: float,
        all_candidates: list,
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

    @staticmethod
    def inject_simplification_trace(container_id: str, glyph_id: str, suggestions: List[str]):
        _global_trace.entries.append({
            "type": "glyph",
            "glyph": glyph_id,
            "action": "simplify",
            "timestamp": time.time(),
            "source": "prediction_engine",
            "context": container_id,
            "detail": {"suggestions": suggestions},
        })

    @staticmethod
    def inject_replay_trace(container_id: str, glyph_id: str, step: str, notes: Optional[str] = None):
        _global_trace.entries.append({
            "type": "glyph",
            "glyph": glyph_id,
            "action": "replay_step",
            "timestamp": time.time(),
            "source": "codex_executor",
            "context": container_id,
            "detail": {"step": step, "notes": notes},
        })

    # === Theorem / Law Check Injection (Symatics v0.2) ===
    def inject_theorem_trace(self, operator: str, summary: str, violations: list, context: dict):
        """
        Structured hook for Symatics theorem-law verification traces.
        """
        theorem_entry = {
            "type": "theorem",
            "engine": "symatics",
            "action": "law_check",
            "operator": operator,
            "timestamp": time.time(),
            "summary": summary,
            "violations": violations or [],
            "context": context or {},
        }
        self.entries.append(theorem_entry)

        # Try persistence (non-blocking)
        try:
            from backend.modules.hexcore.memory_engine import store_memory
            store_memory({
                "label": f"symatics:law_check:{operator}",
                "content": theorem_entry,
            })
        except Exception:
            pass
        # inside CodexTrace.inject_theorem_trace(...)
        try:
            from backend.symatics.theorem_ledger_writer import append_theorem_entry
            append_theorem_entry(theorem_entry)
        except Exception:
            pass

        print(f"[Trace:Theorem] {operator} -> {summary}, violations: {violations or 'none'}")

    # === Legacy Execution Trace ===
    def trace_execution(self, codex_str: str, result: str, context: Optional[dict] = None, source: str = "codex_executor"):
        """Direct hook for Codex executors to log a run."""
        self.record(
            glyph=codex_str,
            context=context or {},
            result=result,
            source=source,
        )


# ✅ Global singleton instance
_global_trace = CodexTrace()


# --- Public API Helpers ---
def log_codex_trace(glyph: str, context: dict, result: str, source: str = "benchmark"):
    _global_trace.record(glyph, context, result, source)


def get_codex_trace():
    return _global_trace.get_trace()


def get_latest_trace(container_id: Optional[str] = None):
    return _global_trace.get_latest_trace(container_id)


# ✅ Execution Path Wrapper for GHXEncoder
def trace_glyph_execution_path(glyph_id: str) -> Dict:
    matching = [e for e in _global_trace.get_trace() if e.get("glyph") == glyph_id]
    return {
        "glyph_id": glyph_id,
        "steps": matching,
        "count": len(matching),
        "latest": matching[-1] if matching else None,
    }


# --- CLI Harness for Dev/Test ---
if __name__ == "__main__":
    print("⚡ Running CodexTrace self-test...")

    ctx = {"container_id": "test-container", "ghx_id": "ghx-001"}
    _global_trace.trace_execution("⊗(R1,R2)", result="R3", context=ctx, source="codex_executor")

    _global_trace.inject_prediction_trace(
        container_id="test-container",
        glyph_id="⊗",
        beam_source="photon",
        predicted_label="⊗",
        confidence=0.93,
        entropy=0.12,
        logic_score=0.88,
        all_candidates=["⊗", "∇", "□"],
    )

    _global_trace.log({
        "action": "executed",
        "source": "glyph_executor",
        "glyph": "⊕",
        "container": "test-container"
    })

    # Theorem trace test
    _global_trace.inject_theorem_trace("⊕", "5/5 passed", [], ctx)

    print(_global_trace.to_json())