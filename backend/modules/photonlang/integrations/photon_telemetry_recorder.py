# ============================================================
# 🧠 Photon Telemetry Recorder
# ------------------------------------------------------------
# Captures, persists, and replays resonance + SQI + QQC states
# across Photon executions.
# 
#  • Called automatically by QuantumFieldCanvas.resonate()
#  • Persists as .ptn (Photon Telemetry Node) archives
#  • Replays symbolic resonance timeline into QFC viewer
#
# ============================================================

from __future__ import annotations
import json, os, asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

# --- Optional QFC live bridge (safe import) -----------------
try:
    from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
except Exception:
    async def trigger_qfc_render(payload: Dict[str, Any], source: str = "telemetry_replay"):
        print(f"[StubQFC] Would trigger QFC render from {source}: {payload.get('id','(no id)')}")


# --- SQI + QQC Integration (optional, defensive) -------------
try:
    from backend.modules.sqi.sqi_scorer import score_sqi
except Exception:
    def score_sqi(state: Dict[str, Any]):
        return {"sqi_score": 1.0, "entropy": 0.0, "coherence": 1.0}

try:
    from backend.modules.qqc.qqc_resonance_bridge import compute_coherence_metrics
except Exception:
    def compute_coherence_metrics(state: Dict[str, Any]):
        return {"qqc_energy": 1.0, "qqc_harmonics": []}


# ============================================================
# 🔹 Utility
# ============================================================
def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


# ============================================================
# 🔹 Telemetry Recorder
# ============================================================
class PhotonTelemetryRecorder:
    """
    Handles saving and replaying of Photon resonance telemetry.
    Integrates with QFC (for visualization) and SQI (for metrics).
    """

    def __init__(self, base_dir: str = "artifacts/telemetry"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    # --------------------------------------------------------
    def record_event(
        self,
        state: Dict[str, Any],
        container_id: Optional[str] = None,
        label: str = "resonance_event",
    ) -> Dict[str, Any]:
        """
        Save a resonance state snapshot (.ptn + .json).
        """
        ts = _now_iso()
        record = {
            "timestamp": ts,
            "container_id": container_id,
            "label": label,
            "state": state,
            "sqi_feedback": score_sqi(state),
            "qqc_feedback": compute_coherence_metrics(state),
        }

        path = os.path.join(
            self.base_dir,
            f"{label}_{ts.replace(':','-').replace('.','_')}.ptn",
        )

        _ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

        print(f"🪶 [PhotonTelemetry] Saved → {path}")
        return record

    # --------------------------------------------------------
    async def replay_event(
        self,
        record_path: str,
        *,
        visualize: bool = True,
        delay_s: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Replay a saved .ptn event back into QFC (and optionally recompute SQI).
        """
        if not os.path.exists(record_path):
            raise FileNotFoundError(record_path)

        with open(record_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        state = data.get("state", {})
        feedback = data.get("sqi_feedback", {})
        label = data.get("label", "replay")

        print(f"🔁 [PhotonTelemetry] Replaying {label} @ {data.get('timestamp')}")

        # Re-score + visualize if enabled
        state["recomputed_sqi"] = score_sqi(state)
        state["recomputed_qqc"] = compute_coherence_metrics(state)

        if visualize:
            try:
                await trigger_qfc_render(
                    {"id": label, "state": state, "metrics": feedback},
                    source="telemetry_replay",
                )
            except Exception as e:
                print(f"⚠️ [PhotonTelemetry] Visualization error: {e}")

        await asyncio.sleep(delay_s)
        return state

    # --------------------------------------------------------
    async def replay_all(self, *, visualize: bool = True, delay_s: float = 0.3):
        """
        Replay all telemetry events in chronological order.
        """
        files = sorted(
            f for f in os.listdir(self.base_dir) if f.endswith(".ptn")
        )
        for fn in files:
            await self.replay_event(os.path.join(self.base_dir, fn), visualize=visualize, delay_s=delay_s)


# ============================================================
# 🔹 Global Recorder
# ============================================================
RECORDER = PhotonTelemetryRecorder()