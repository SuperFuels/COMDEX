# ============================================================
# 🌌 Photon Timeline Replay Layer
# ============================================================
# Enables reloading .ptn telemetry snapshots and replaying them into
# QuantumFieldCanvas (QFC), SQI, and QQC systems for symbolic timelines.
# Now includes optional Workspace Reinjection for SCI IDE + Container sync.

from __future__ import annotations
import json
import os
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List

from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render

# Optional integrations -------------------------------------------------------
try:
    from backend.modules.photonlang.interpreter import QuantumFieldCanvas
except Exception:
    class QuantumFieldCanvas:
        def __init__(self, *_, **__): self.state = {}
        def resonate(self, seq, intensity=1.0, container_id=None):
            self.state["resonance"] = {"seq": seq, "intensity": intensity}
            return self.state["resonance"]

try:
    from backend.modules.sqi.sqi import SQI
except Exception:
    class SQI:
        @staticmethod
        def optimize():
            return {"sqi_score": 1.0, "entropy": 0.0, "coherence": 1.0}

try:
    from backend.modules.qqc.qqc_resonance_bridge import QQCResonanceBridge
except Exception:
    class QQCResonanceBridge:
        @staticmethod
        def emit(intensity: float):
            print(f"[Stub QQC] Replayed intensity {intensity}")
            return {"qqc_energy": intensity}

# Optional SCI / Container Workspace Integrations ----------------------------
try:
    from backend.modules.sci.sci_core import SCIWorkspace
    from backend.modules.container.container_workspace_loader import load_container_workspace
except Exception:
    class SCIWorkspace:
        def __init__(self, container_id="default"): self.container_id = container_id
        def inject_state(self, state): print(f"[Stub SCIWorkspace] Injected state -> {self.container_id}")
    def load_container_workspace(container_id, state): print(f"[StubContainer] Loaded {container_id}")

# -----------------------------------------------------------------------------
TELEMETRY_DIR = "artifacts/telemetry"


# ============================================================
# 📂 Load & Parse Telemetry
# ============================================================
def load_from_ptn(path: str) -> Dict[str, Any]:
    """Load a saved .ptn telemetry file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Telemetry file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def list_available_snapshots(limit: int = 10) -> List[str]:
    """Return the most recent saved telemetry .ptn files."""
    if not os.path.exists(TELEMETRY_DIR):
        return []
    files = sorted(
        [os.path.join(TELEMETRY_DIR, f) for f in os.listdir(TELEMETRY_DIR) if f.endswith(".ptn")],
        key=os.path.getmtime,
        reverse=True,
    )
    return files[:limit]


# ============================================================
# 🌀 Replay Engine (single frame)
# ============================================================
async def replay_snapshot(
    path: str,
    *,
    broadcast: bool = True,
    delay: float = 0.5,
    reinject: bool = True,
    container_id: str = "default_sci_session",
) -> Dict[str, Any]:
    """
    Replay a single photon resonance snapshot.
    - Recreates the QuantumFieldCanvas state
    - Emits QFC visuals if broadcast=True
    - Optionally reinjects the state into SCI/Container
    """
    data = load_from_ptn(path)
    state = data.get("state", {}).get("resonance", {})
    seq = state.get("seq", "")
    intensity = state.get("intensity", 1.0)
    container_id = data.get("container_id", container_id)

    qfc = QuantumFieldCanvas()
    replay_state = qfc.resonate(seq, intensity=intensity)

    sqi = SQI.optimize()
    qqc = QQCResonanceBridge.emit(intensity)

    # Reinjection layer - rehydrate SCI and container state
    if reinject:
        try:
            load_container_workspace(container_id, state=data.get("state", {}))
            sci_ws = SCIWorkspace(container_id)
            sci_ws.inject_state(data.get("state", {}))
            print(f"♻️ Reinjected workspace for [{container_id}] from {os.path.basename(path)}")
        except Exception as e:
            print(f"⚠️ Reinjection failed for {path}: {e}")

    frame = {
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "seq": seq,
        "intensity": intensity,
        "sqi_feedback": sqi,
        "qqc_feedback": qqc,
        "replayed_from": os.path.basename(path),
    }

    if broadcast:
        try:
            await trigger_qfc_render(
                {"type": "timeline_frame", "frame": frame, "label": "photon_replay"},
                source="timeline_replay"
            )
            print(f"🌀 QFC frame broadcasted: {path}")
        except Exception as e:
            print(f"⚠️ Failed to broadcast replay frame: {e}")

    if delay > 0:
        await asyncio.sleep(delay)

    return frame


# ============================================================
# 🎞️ Full Timeline Replay (multi-frame)
# ============================================================
async def replay_timeline(
    limit: int = 10,
    broadcast: bool = True,
    delay: float = 0.8,
    reinject: bool = True,
    container_id: str = "default_sci_session",
) -> List[Dict[str, Any]]:
    """
    Replay multiple saved .ptn frames in chronological order,
    rebuilding symbolic cognition timelines for QFC visualization
    and optionally restoring workspace + SCI IDE state.
    """
    snapshots = list_available_snapshots(limit)
    if not snapshots:
        print("⚠️ No saved resonance telemetry snapshots found.")
        return []

    snapshots.reverse()  # old -> new
    frames: List[Dict[str, Any]] = []
    print(f"🎞️ Replaying {len(snapshots)} frames (reinjection={'on' if reinject else 'off'})...")

    for path in snapshots:
        frame = await replay_snapshot(
            path,
            broadcast=broadcast,
            delay=delay,
            reinject=reinject,
            container_id=container_id,
        )
        frames.append(frame)

    print("✅ Timeline replay complete.")
    return frames