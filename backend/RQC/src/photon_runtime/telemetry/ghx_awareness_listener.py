"""
Tessaris RQC — GHX Awareness Listener
──────────────────────────────────────────────
Phase 6.5 · Awareness feed consumer + auto-export.

Listens to the MorphicLedger v2 file via GHX Feed,
prints Φ(t), R(t), S in real time, logs awareness frames
to CodexMetrics + Morphic Ledger summary,
and triggers automatic LaTeX Appendix export when closure stabilizes.
"""

import time
import json
from pathlib import Path

from backend.RQC.src.photon_runtime.telemetry.ghx_awareness_feed import get_latest_awareness_frame

# Optional import — only if you later add visualization hooks
# from backend.RQC.src.photon_runtime.telemetry.utils import render_awareness_plot

# Safe import / fallback for CodexMetrics integration
try:
    from backend.modules.codex.codexmetrics import record_event
except ImportError:
    def record_event(event_name: str, payload: dict = None):
        payload = payload or {}
        print(f"[CodexMetrics] Event: {event_name} {json.dumps(payload, ensure_ascii=False)}")
        return {"timestamp": time.time(), "event": event_name, "payload": payload}

# Import LaTeX exporter for auto-update hook
try:
    from backend.RQC.src.photon_runtime.exporters import latex_appendix_c_exporter as appendix_exporter
except ImportError:
    appendix_exporter = None
    print("⚠️  LaTeX exporter not available; auto-export disabled.")

LEDGER_PATH = Path("data/ledger/rqc_live_telemetry.jsonl")
SUMMARY_FILE = Path("data/ledger/awareness_sessions_summary.jsonl")
REFRESH_INTERVAL = 2.0  # seconds
EXPORT_DEBOUNCE = 30.0  # seconds between auto-exports

#───────────────────────────────────────────────
#  Main listener
#───────────────────────────────────────────────
def run_listener(duration: float = 60.0):
    print("🧠 GHX Awareness Listener — Streaming Φ(t), R(t), S …")
    t0 = time.time()
    last_export_ts = 0.0

    while time.time() - t0 < duration:
        frame = get_latest_awareness_frame(LEDGER_PATH)
        if frame:
            # Safe numeric defaults
            phi = frame.get("Phi") or 0.0
            res = frame.get("resonance_index") or 0.0
            stab = frame.get("stability") or 0.0
            gain = frame.get("gain") or 0.0
            state = frame.get("closure_state") or "?"

            # 🧠 Clean formatted printout
            print(f"[Φ={phi:.6f}] [R={res:.6f}] [S={stab}] [g={gain:.2f}] [state={state}]")

            # Record to CodexMetrics or fallback
            record_event("GHX::awareness_frame", frame)

            # 🧩 Phase 6.5 — Auto-export trigger
            if state == "stable" and time.time() - last_export_ts > EXPORT_DEBOUNCE:
                try:
                    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
                    with SUMMARY_FILE.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(frame) + "\n")
                    print("📦 Logged stable session → awareness_sessions_summary.jsonl")

                    if appendix_exporter:
                        appendix_exporter.export_latest()
                        print("📜 Appendix C auto-updated.")
                    else:
                        print("⚠️  Exporter unavailable — skipped LaTeX update.")

                    last_export_ts = time.time()
                except Exception as e:
                    print(f"❌ Auto-export failed: {e}")
        else:
            print("[GHXFeed] Waiting for next frame …")

        time.sleep(REFRESH_INTERVAL)

#───────────────────────────────────────────────
#  Entry point
#───────────────────────────────────────────────
if __name__ == "__main__":
    try:
        run_listener(duration=60.0)
    except KeyboardInterrupt:
        print("\n⏹️ Listener stopped.")