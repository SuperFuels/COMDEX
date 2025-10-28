#!/usr/bin/env python3
"""
🛑 InterruptionManager — Phase 63: Resonant Override Control
───────────────────────────────────────────────────────────────
Supervises all interruption, contradiction, and override signals
within the Tessaris cognitive core.

Responsibilities:
  • Monitor external stop or override commands
  • Detect internal contradictions / ethical re-evaluations
  • Snapshot and pause current ActionSwitch context
  • Forward re-evaluation request to Tessaris Reasoner
  • Resume or abort execution based on Θ + EthicsEngine response

Integrations:
  - Θ heartbeat for timing and phase sync
  - ActionSwitch control channel
  - EthicsEngine + Resonant Dashboard
  - Tessaris Reasoner for cognitive arbitration
"""

import time, json, threading, signal
from pathlib import Path
from datetime import datetime
from backend.modules.consciousness.ethics_engine import EthicsEngine
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.action_switch.action_switch import ActionSwitch


class InterruptionManager:
    def __init__(self):
        self.Theta = ResonanceHeartbeat(namespace="interrupt", base_interval=0.8)
        self.ethics = EthicsEngine()
        self.rmc = ResonantMemoryCache()
        self.action_switch = ActionSwitch()

        self.override_flag = False
        self._lock = threading.Lock()
        self.snapshot_path = Path("data/snapshots/context_snapshot.json")
        self.log_path = Path("data/analysis/interruption_log.jsonl")
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        # Register system signal handlers
        signal.signal(signal.SIGINT, self._handle_external_interrupt)
        signal.signal(signal.SIGTERM, self._handle_external_interrupt)

    # ------------------------------------------------------------
    # External signal interception
    # ------------------------------------------------------------
    def _handle_external_interrupt(self, signum, frame):
        """Handles SIGINT/SIGTERM from environment."""
        print(f"🛑 External interrupt ({signum}) detected — initiating snapshot.")
        self.trigger(reason="external_signal", source="system")

    # ------------------------------------------------------------
    # Core trigger (INT1–INT2)
    # ------------------------------------------------------------
    def trigger(self, reason: str, source: str = "unknown", details: dict | None = None):
        with self._lock:
            self.override_flag = True
            self._snapshot_context(reason, source)
            self._evaluate(reason, source, details)

    # ------------------------------------------------------------
    # Snapshot & pause (INT3)
    # ------------------------------------------------------------
    def _snapshot_context(self, reason: str, source: str):
        """Capture current ActionSwitch + Θ state."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "source": source,
            "theta": self.Theta.snapshot(),
            "active_action": self.action_switch.current_action(),
            "rmc_state": self.rmc.summary(),
        }
        self.snapshot_path.write_text(json.dumps(snapshot, indent=2))
        print(f"💾 Snapshot saved → {self.snapshot_path}")

        # Log to telemetry
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "snapshot", **snapshot}) + "\n")

        # Pause all outgoing actions
        try:
            self.action_switch.pause_all()
        except Exception as e:
            print(f"[INTERRUPTION] ⚠ Failed to pause actions: {e}")

    # ------------------------------------------------------------
    # Ethical & Reasoner evaluation (INT4)
    # ------------------------------------------------------------
    def _evaluate(self, reason: str, source: str, details: dict | None = None):
        """Consult EthicsEngine + Reasoner for go/no-go decision."""
        event = {
            "action": reason,
            "timestamp": time.time(),
            "source": source,
        }
        result = self.ethics.evaluate(reason)
        decision = "abort" if "VETOED" in result["result"] else "resume"

        self.Theta.event(
            "interruption_evaluation",
            reason=reason,
            decision=decision,
            confidence=result.get("confidence", 0.5),
            matched_laws=result.get("matched_laws", []),
        )

        print(f"[Θ] Interruption evaluation → decision={decision}, confidence={result.get('confidence', 0.5)}")

        # Forward to Tessaris Reasoner if available
        try:
            from backend.modules.reasoner.tessaris_reasoner import TessarisReasoner
            reasoner = TessarisReasoner()
            reasoner.submit_event("interruption", {"reason": reason, "decision": decision})
        except Exception as e:
            print(f"[INTERRUPTION] ⚠ Reasoner relay failed: {e}")

        # Proceed to resolve
        self._resolve(decision)

    # ------------------------------------------------------------
    # Resume or abort (INT5)
    # ------------------------------------------------------------
    def _resolve(self, decision: str):
        """Resolve interruption: resume or abort."""
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
    # Continuous monitoring loop
    # ------------------------------------------------------------
    def monitor_loop(self, interval: float = 1.5):
        """Monitors internal contradiction signals + external overrides."""
        print("🧭 InterruptionManager active — monitoring for contradictions and overrides.")
        while True:
            time.sleep(interval)
            if self.override_flag:
                continue  # skip during ongoing interruption

            # Internal contradiction sampling
            try:
                coherence = self.rmc.get_average("coherence")
                entropy = self.rmc.get_average("entropy")
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

    print("🛑 InterruptionManager demo running. Press Ctrl+C to trigger.")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        mgr.trigger(reason="manual_interrupt", source="keyboard")