# ================================================================
# 🧪 QuantPy v0.5 Validation Runner - GHX↔Habit↔CodexMetrics Chain
# ================================================================
"""
Runs an integrated regression validation for QuantPy v0.5:
    1. Replays a .photo packet via QPhotonRuntimeGHX
    2. Syncs habit feedback via GHXHabitAutoBridge
    3. Updates CodexMetrics overlay
Outputs:
    data/telemetry/qpy_v0_5_validation.json
"""

import json, time, logging
from pathlib import Path

from backend.quant.qphoton.qphoton_runtime_ghx import QPhotonRuntimeGHX
from backend.bridges.ghx_habit_auto_bridge import GHXHabitAutoBridge
from backend.bridges.ghx_codexmetrics_bridge import GHXCodexMetricsBridge as CodexMetricsBridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path("data/telemetry/qpy_v0_5_validation.json")

def run_validation():
    t0 = time.time()

    # 1️⃣ GHX photon replay
    packet_path = Path("data/quantum/qcompiler_output/test_compile.photo")
    runtime = QPhotonRuntimeGHX()
    packet = runtime.load_packet(packet_path)
    runtime.execute(packet)
    runtime.export_log(session_id=packet_path.stem)
    ghx_summary = runtime.export_summary(session_id=packet_path.stem)

    # 2️⃣ Habit auto-feedback sync
    habit_bridge = GHXHabitAutoBridge()
    habit_snapshot = habit_bridge.sync_to_habit()

    # 3️⃣ CodexMetrics overlay update
    codex = CodexMetricsBridge()
    codex_snapshot = codex.sync_overlay()

    # 🧾 Aggregate validation summary
    summary = {
        "timestamp": time.time(),
        "duration_s": round(time.time() - t0, 3),
        "ghx_summary": ghx_summary,
        "habit_snapshot": habit_snapshot,
        "codex_overlay": codex_snapshot,
        "schema": "QuantPyV05Validation.v1",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(OUTPUT_PATH, "w"), indent=2)
    logger.info(f"[QuantPyV0.5] Validation summary -> {OUTPUT_PATH}")
    print(json.dumps(summary, indent=2))
    print("✅ QuantPy v0.5 regression validation complete.")
    return summary


if __name__ == "__main__":
    run_validation()