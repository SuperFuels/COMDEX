"""
AION Heartbeat -> QQC Coherence Link
────────────────────────────────────
This module links AION's heartbeat scheduler to the QQC Resonant Logic Kernel
diagnostic pipeline. Every N heartbeats (dynamically adjusted), the RLK
validator runs and updates the Φ-stability telemetry via AION's
CoherenceTracker, emits Φ-cognitive metrics, and engages the AION Resonance
Governor for real-time self-regulation.

Runtime Behavior:
  * Every N beats -> run RLK diagnostic (adaptive interval)
  * Log pass_rate, ε, and diagnostic status
  * Update Φ_stability_index via record_coherence()
  * Emit Φ_COGNITION telemetry snapshot via record_cognitive_metrics()
  * Regulate QQC tolerance & audit cadence via ResonanceGovernor
  * Reflect any parameter changes immediately in the live QQC state
  * Persist and restore last known ε / N state across restarts
  * Push symbolic resonance insights -> CodexTrace
  * Verify πs closure via Symatic Closure Verifier
"""

import asyncio
from datetime import datetime, timezone

# ──────────────────────────────────────────────────────────────
# Core imports
# ──────────────────────────────────────────────────────────────
from backend.QQC.core.rlk_state import get_state
from backend.AION.governance.resonance_governor import regulate


# ──────────────────────────────────────────────────────────────
async def heartbeat_loop():
    """Asynchronous heartbeat with live adaptive frequency and tolerance."""
    state = get_state()

    print("[AION::Heartbeat] Starting coherence-linked heartbeat loop ...")
    print(f"[AION::Heartbeat] Restored last QQC state -> ε={state['tolerance']:.4f}, "
          f"N={state['audit_interval']} beats")

    beat = 0

    while True:
        beat += 1
        timestamp = datetime.now(timezone.utc).isoformat()
        state = get_state()
        current_interval = int(state.get("audit_interval", 10))
        print(f"[♥] Beat {beat} - {timestamp}")

        # ──────────────────────────────────────────────────────────────
        # Trigger RLK diagnostic every current_interval beats
        # ──────────────────────────────────────────────────────────────
        if beat % current_interval == 0:
            print(f"[AION::Heartbeat] Triggering QQC RLK self-audit at beat {beat} ...")

            try:
                from backend.QQC.diagnostics.boot_sequence import run_rlk_diagnostic
                from backend.AION.telemetry.coherence_tracker import record_coherence
                from backend.AION.telemetry.cognitive_metrics import record_cognitive_metrics
                from backend.modules.codex.verifiers.symatic_closure_verifier import verify_symatic_closure

                # Run RLK diagnostic (async-aware)
                report = await run_rlk_diagnostic(post_to_aion=True, verbose=False)

                pass_rate = float(report.get("pass_rate", 0.0))
                eps = float(report.get("tolerance") or report.get("final_tolerance") or 0.0)
                status = report.get("status", "unknown")

                # Update coherence telemetry
                summary = record_coherence(pass_rate, eps, status)
                print(f"[AION::Heartbeat] RLK self-audit -> {status.upper()} "
                      f"(Φ={summary['Φ_stability_index']:.3f}, pass_avg={summary['rolling_avg_pass']:.3f})")

                # Post Φ-cognitive metrics
                try:
                    record_cognitive_metrics()
                except Exception as inner_e:
                    print(f"[AION::Heartbeat] ⚠ Cognitive metrics failed: {inner_e}")

                # Engage Resonance Governor - adaptive parameter regulation
                try:
                    regulate()

                    # Push resonance insight to CodexTrace
                    from backend.modules.codex.bridges.resonant_insight_bridge import push_to_codextrace
                    push_to_codextrace()

                    # Verify πs closure
                    verify_symatic_closure()

                except Exception as inner_e:
                    print(f"[AION::Heartbeat] ⚠ Resonant bridge or verifier failed: {inner_e}")

            except Exception as e:
                print(f"[AION::Heartbeat] ⚠ Self-audit failed: {e}")

        # ──────────────────────────────────────────────────────────────
        # Maintain steady heartbeat rhythm (adaptive timing under review)
        # ──────────────────────────────────────────────────────────────
        await asyncio.sleep(6.0)


# ──────────────────────────────────────────────────────────────
def start_heartbeat():
    """Convenience synchronous launcher."""
    asyncio.run(heartbeat_loop())


# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    start_heartbeat()