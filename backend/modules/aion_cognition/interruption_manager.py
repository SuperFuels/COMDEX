#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛑 InterruptionManager — Phase 63 + (A7 Complete)
───────────────────────────────────────────────────────────────
Conscious override decision engine for Tessaris Core.

Responsibilities:
  • Monitor external stop or override commands
  • Detect internal contradictions / ethical re-evaluations
  • Snapshot + pause ActionSwitch context
  • Consult EthicsEngine + TessarisReasoner for arbitration
  • Resume or abort execution per Θ consensus
"""

import time, json, threading, signal
from pathlib import Path
from datetime import datetime

from backend.modules.consciousness.ethics_engine import EthicsEngine
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_cognition.action_switch import ActionSwitch


class InterruptionManager:
    def __init__(self):
        # Resonant state and cognitive subsystems
        self.Theta = ResonanceHeartbeat(namespace="interrupt")
        self.ethics = EthicsEngine()
        self.rmc = ResonantMemoryCache()
        self.action_switch = ActionSwitch()

        # State control
        self.override_flag = False
        self._lock = threading.Lock()

        # Storage and paths
        self.snapshot_path = Path("data/snapshots/context_snapshot.json")
        self.log_path = Path("data/analysis/interruption_log.jsonl")
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # OS signal handlers
        signal.signal(signal.SIGINT, self._handle_external_interrupt)
        signal.signal(signal.SIGTERM, self._handle_external_interrupt)

    # ------------------------------------------------------------
    def _handle_external_interrupt(self, signum, frame):
        """Handles SIGINT/SIGTERM from environment."""
        print(f"🛑 External interrupt ({signum}) detected — initiating snapshot.")
        self.trigger(reason="external_signal", source="system")

    # ------------------------------------------------------------
    def trigger(self, reason: str, source: str = "unknown", details: dict | None = None):
        """Primary trigger entry — sets override flag and initiates evaluation."""
        with self._lock:
            self.override_flag = True
            self._snapshot_context(reason, source)
            self._evaluate(reason, source, details)

    # ------------------------------------------------------------
    def _snapshot_context(self, reason: str, source: str):
        """Capture ActionSwitch + Θ state for potential rollback."""
        # Safely gather summaries
        try:
            rmc_state = self.rmc.summary()
        except Exception:
            # fallback safe minimal summary
            rmc_state = {
                "avg_coherence": getattr(self.rmc, "avg_coherence", 0.0),
                "avg_entropy": getattr(self.rmc, "avg_entropy", 0.0),
                "entries": len(getattr(self.rmc, "cache", {}))
            }

        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "source": source,
            "theta": getattr(self.Theta, "namespace", "interrupt"),
            "active_action": self._safe_action_name(),
            "rmc_state": rmc_state,
        }

        # Persist snapshot
        self.snapshot_path.write_text(json.dumps(snapshot, indent=2))
        print(f"💾 Snapshot saved → {self.snapshot_path}")

        # Log to JSONL file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "snapshot", **snapshot}) + "\n")

        # Attempt to pause ongoing actions
        try:
            self.action_switch.pause_all()
        except Exception as e:
            print(f"[INTERRUPTION] ⚠ Failed to pause actions: {e}")

    # ------------------------------------------------------------
    def _safe_action_name(self):
        """Returns the current ActionSwitch action or 'idle'."""
        try:
            cur = self.action_switch.current_action()
            return cur if isinstance(cur, str) else getattr(cur, "name", "unknown")
        except Exception:
            return "idle"

    # ------------------------------------------------------------
    def _evaluate(self, reason: str, source: str, details: dict | None = None):
        """Consult EthicsEngine + Reasoner for go/no-go arbitration."""
        ethics_result = self.ethics.evaluate(reason)
        ethics_conf = ethics_result.get("confidence", 0.5)
        ethics_ok = "VETOED" not in ethics_result.get("result", "")

        # Fuse goal vs ethics arbitration through TessarisReasoner
        try:
            from backend.modules.aion_reasoning.tessaris_reasoner import TessarisReasoner
            reasoner = TessarisReasoner()
            goal_state = (details or {}).get("goal", "undefined")
            motive = (details or {}).get("motivation", {})
            decision_ctx = {"goal": goal_state, "why": reason, "motivation": motive}
            reasoned = reasoner.reason(decision_ctx, motive)
            goal_conf = reasoned.get("confidence", 0.5)
            ethics_score = reasoned.get("ethics_score", 1.0)
        except Exception as e:
            print(f"[INTERRUPTION] ⚠ Reasoner arbitration failed: {e}")
            goal_conf, ethics_score = 0.5, ethics_conf

        # Resonant arbitration weighting
        entropy = self._safe_rmc_avg("entropy")
        resonance_factor = round(((ethics_conf + goal_conf + ethics_score) / 3) * (1 - entropy * 0.3), 3)
        decision = "resume" if ethics_ok and resonance_factor > 0.45 else "abort"

        # Emit Theta event for dashboard
        try:
            self.Theta.event(
                "interruption_arbitration",
                reason=reason,
                decision=decision,
                ethics_conf=ethics_conf,
                goal_conf=goal_conf,
                resonance=resonance_factor,
            )
        except Exception:
            pass

        print(
            f"[Θ] Interruption arbitration → decision={decision}, "
            f"resonance={resonance_factor:.3f}, ethics={ethics_conf:.3f}, goal={goal_conf:.3f}"
        )

        # Persist arbitration record
        record = {
            "timestamp": time.time(),
            "reason": reason,
            "decision": decision,
            "ethics_conf": ethics_conf,
            "goal_conf": goal_conf,
            "resonance": resonance_factor,
            "entropy": entropy,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "evaluation", **record}) + "\n")

        self._resolve(decision)

    # ------------------------------------------------------------
    def _safe_rmc_avg(self, key: str) -> float:
        """Safe getter for RMC averaged metrics."""
        try:
            if hasattr(self.rmc, "get_average"):
                return self.rmc.get_average(key) or 0.5
            # fallback approximation
            if hasattr(self.rmc, "cache") and self.rmc.cache:
                vals = [v.get(key, 0.5) for v in self.rmc.cache.values() if isinstance(v, dict)]
                return sum(vals) / len(vals) if vals else 0.5
        except Exception:
            pass
        return 0.5

    # ------------------------------------------------------------
    def _resolve(self, decision: str):
        """Finalize resolution — resume or abort execution."""
        if decision == "resume":
            print("✅ Interruption cleared — resuming ActionSwitch execution.")
            try:
                self.action_switch.resume_all()
            except Exception as e:
                print(f"[INTERRUPTION] ⚠ Resume error: {e}")
        else:
            print("⛔ Interruption vetoed — aborting current ActionSwitch execution.")
            try:
                self.action_switch.abort_all()
            except Exception as e:
                print(f"[INTERRUPTION] ⚠ Abort error: {e}")
        self.override_flag = False

    # ------------------------------------------------------------
    def monitor_loop(self, interval: float = 1.5):
        """Continuously monitors for internal contradictions + entropy drift."""
        print("🧭 InterruptionManager active — monitoring contradictions + overrides.")
        while True:
            time.sleep(interval)
            if self.override_flag:
                continue
            try:
                coherence = self._safe_rmc_avg("coherence")
                entropy = self._safe_rmc_avg("entropy")
                if entropy - coherence > 0.4:
                    print("⚠️ Internal contradiction detected (entropy spike).")
                    self.trigger(reason="internal_contradiction", source="rmc_field")
            except Exception:
                continue


# ───────────────────────────────────────────────
# Demo mode
# ───────────────────────────────────────────────
if __name__ == "__main__":
    mgr = InterruptionManager()
    t = threading.Thread(target=mgr.monitor_loop, daemon=True)
    t.start()
    print("🛑 InterruptionManager demo running — press Ctrl + C to trigger.")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        mgr.trigger(reason="manual_interrupt", source="keyboard")