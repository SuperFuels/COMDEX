#!/usr/bin/env python3
# ================================================================
# 🧬 ReflexMemory — Phase 63 Reflex–Reasoner Fusion (Unified)
# ================================================================
# Combines original telemetry logging with new RMC resonance logic.
# Responsibilities:
#   • Persist reflex traces (action/context/decision/outcome)
#   • Compute SQI / ΔΦ / entropy + success rate
#   • Maintain rolling stability & drift averages
#   • Feed resonance data to ResonantMemoryCache
#   • Provide last_state + summary for TessarisReasoner
# ================================================================

import json, time, math, logging
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Any, List, Optional

from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

logger = logging.getLogger(__name__)

OUT = Path("data/telemetry/reflex_memory.jsonl")


class ReflexMemory:
    def __init__(self, limit: int = 500):
        self.limit = limit
        self.traces: List[Dict[str, Any]] = []
        self.rmc = ResonantMemoryCache()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------
    def _load(self):
        """Load recent reflex traces from disk (if present)."""
        if not OUT.exists():
            return
        try:
            with open(OUT, "r", encoding="utf-8") as f:
                self.traces = [json.loads(l) for l in f if l.strip()][-self.limit :]
            logger.info(f"[ReflexMemory] Loaded {len(self.traces)} previous entries.")
        except Exception as e:
            logger.warning(f"[ReflexMemory] Failed to load prior traces: {e}")

    # ------------------------------------------------------------
    def record(self, action: str, context: Dict[str, Any], decision: Dict[str, Any], outcome: Dict[str, Any]):
        """Add new reflex record and push resonance metrics."""
        trace = {
            "timestamp": time.time(),
            "action": action,
            "context": context,
            "decision": decision,
            "outcome": outcome,
        }
        self.traces.append(trace)
        if len(self.traces) > self.limit:
            self.traces.pop(0)

        try:
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace) + "\n")
            logger.info(f"[ReflexMemory] Recorded {action} Θ={decision.get('theta', 0):.3f}")
        except Exception as e:
            logger.warning(f"[ReflexMemory] Failed to write trace: {e}")

        # Update resonance metrics
        try:
            sqi = outcome.get("sqi", decision.get("theta", 0.0))
            delta_phi = outcome.get("delta_phi", 0.0)
            entropy = outcome.get("entropy", 0.5)

            rho_val = 0.0
            if context and isinstance(context, dict):
                resonance = context.get("resonance") or {}
                if isinstance(resonance, dict):
                    rho_val = resonance.get("ρ") or resonance.get("rho") or 0.0

            self.rmc.push_sample(
                source=action,
                sqi=sqi,
                rho=rho_val,
                delta=delta_phi,
                entropy=entropy
            )
            self.rmc.save()
        except Exception as e:
            logger.warning(f"[ReflexMemory] Failed to push to RMC: {e}")

    # ------------------------------------------------------------
    def recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return n most recent reflex traces."""
        return self.traces[-n:]

    # ------------------------------------------------------------
    def get_last_state(self) -> Optional[Dict[str, Any]]:
        """Return condensed state for last reflex action."""
        if not self.traces:
            return None
        last = self.traces[-1]
        outcome = last.get("outcome", {})
        return {
            "sqi": outcome.get("sqi", 0.6),
            "delta_phi": outcome.get("delta_phi", 0.0),
            "entropy": outcome.get("entropy", 0.5),
            "response_time": outcome.get("response_time", 0.25),
            "timestamp": last["timestamp"],
        }

    # ------------------------------------------------------------
    def summarize(self) -> Dict[str, Any]:
        """Compute base success rate summary."""
        total = len(self.traces)
        successes = sum(1 for t in self.traces if t["outcome"].get("success"))
        return {
            "total_actions": total,
            "success_rate": (successes / total) if total else 0.0,
        }

    # ------------------------------------------------------------
    def get_summary(self, window: int = 100) -> Dict[str, Any]:
        """Extended stability + drift summary for Genomic Telemetry."""
        if not self.traces:
            return {"count": 0, "avg_sqi": 0.0, "avg_delta": 0.0, "avg_entropy": 0.0, "stability": 0.0}
        subset = self.traces[-window:]
        sqis = [r["outcome"].get("sqi", 0.6) for r in subset]
        deltas = [r["outcome"].get("delta_phi", 0.0) for r in subset]
        entropies = [r["outcome"].get("entropy", 0.5) for r in subset]

        avg_sqi = round(mean(sqis), 3)
        avg_delta = round(mean(deltas), 3)
        avg_entropy = round(mean(entropies), 3)
        stability = round(max(0.0, 1.0 - pstdev(sqis + entropies) * 0.5), 3)

        summary = {
            "count": len(subset),
            "avg_sqi": avg_sqi,
            "avg_delta": avg_delta,
            "avg_entropy": avg_entropy,
            "stability": stability,
        }
        summary.update(self.summarize())
        return summary

    # ------------------------------------------------------------
    def export_summary(self, out_path: str = "data/reflex/reflex_summary.json"):
        """Export compact summary for dashboards."""
        summary = self.get_summary()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"[ReflexMemory] Exported summary → {out_path}")
        return summary


# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rm = ReflexMemory()
    summary = rm.get_summary()
    print("🧬 ReflexMemory summary:", json.dumps(summary, indent=2))