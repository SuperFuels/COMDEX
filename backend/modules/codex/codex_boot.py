# 📁 codex_boot.py

from datetime import datetime
from backend.modules.codex.codex_runtime_loop import CodexRuntimeLoop
from backend.modules.codex.codex_memory_triggers import CodexMemoryTrigger
from backend.modules.codex.codex_autopilot import CodexAutopilot
from backend.modules.codex.codex_websocket_interface import send_codex_ws_event
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ Register with DNA switch
DNA_SWITCH.register(__file__)

def boot_codex_runtime(mode="once"):
    """
    Boot Codex symbolic runtime and supporting modules.
    Mode options:
      - "once": run one cycle of each
      - "loop": launch runtime loop (blocking)
    """
    print("🚀 Booting Codex Runtime...")
    metrics = CodexMetrics()
    timestamp = datetime.utcnow().isoformat()

    try:
        runtime = CodexRuntimeLoop()
        trigger = CodexMemoryTrigger()
        autopilot = CodexAutopilot()

        if mode == "loop":
            runtime.loop()
        else:
            runtime.run_once()
            trigger.scan_and_trigger()
            autopilot.evolve()

        metrics.record_boot()
        send_codex_ws_event("codex_boot", {
            "status": "ok",
            "mode": mode,
            "timestamp": timestamp,
            "message": "Codex Runtime initialized"
        })

        print("✅ Codex Runtime initialized.")

    except Exception as e:
        send_codex_ws_event("codex_boot", {
            "status": "error",
            "timestamp": timestamp,
            "message": str(e)
        })
        print(f"❌ Codex boot failed: {e}")