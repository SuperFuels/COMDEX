# ============================================================
# 🌌 Photon Timeline Replay Layer (lazy imports + deterministic/quiet aware)
# ============================================================
# Enables reloading .ptn telemetry snapshots and replaying them into
# QuantumFieldCanvas (QFC), SQI, and QQC systems for symbolic timelines.
# Includes optional Workspace Reinjection for SCI IDE + Container sync.
#
# IMPORTANT:
# - No heavy runtime imports at module import-time (pytest/CI safe)
# - Deterministic time when TESSARIS_DETERMINISTIC_TIME=1
# ============================================================

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Env gates
# -----------------------------------------------------------------------------
def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


def _now_iso() -> str:
    if _deterministic_time_enabled():
        return "0000-00-00T00:00:00.000Z"
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


# -----------------------------------------------------------------------------
# Optional hook: QFC render (keep import-time light)
# -----------------------------------------------------------------------------
async def _trigger_qfc_render(payload: Dict[str, Any], source: str = "timeline_replay") -> None:
    try:
        from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render  # heavy-ish
        await trigger_qfc_render(payload, source=source)
    except Exception:
        if not _quiet_enabled():
            print(f"[StubQFC] Would trigger QFC render from [{source}] -> keys={list(payload.keys())}")


# -----------------------------------------------------------------------------
# Lazy optional integrations (no import-time bring-up)
# -----------------------------------------------------------------------------
def _get_quantum_field_canvas_cls():
    try:
        from backend.modules.photonlang.interpreter import QuantumFieldCanvas
        return QuantumFieldCanvas
    except Exception:
        class QuantumFieldCanvas:  # type: ignore
            def __init__(self, *_, **__):
                self.state: Dict[str, Any] = {}

            def resonate(self, seq: str, intensity: float = 1.0, container_id: Optional[str] = None):
                self.state["resonance"] = {"seq": seq, "intensity": intensity, "container_id": container_id}
                return self.state["resonance"]
        return QuantumFieldCanvas


def _compute_sqi_optimize() -> Dict[str, Any]:
    try:
        from backend.modules.sqi.sqi import SQI
        return SQI.optimize()
    except Exception:
        return {"sqi_score": 1.0, "entropy": 0.0, "coherence": 1.0}


def _emit_qqc(intensity: float) -> Dict[str, Any]:
    try:
        from backend.modules.qqc.qqc_resonance_bridge import QQCResonanceBridge
        return QQCResonanceBridge.emit(float(intensity))
    except Exception:
        if not _quiet_enabled():
            print(f"[Stub QQC] Replayed intensity {intensity}")
        return {"qqc_energy": float(intensity)}


def _reinjection_modules():
    """
    Import SCI/container reinjection only when reinject=True.
    Keeps pytest/CI import-time clean.
    """
    from backend.modules.sci.sci_core import SCIWorkspace
    from backend.modules.container.container_workspace_loader import load_container_workspace
    return SCIWorkspace, load_container_workspace


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
        return json.load(f)


def list_available_snapshots(limit: int = 10) -> List[str]:
    """Return the most recent saved telemetry .ptn files."""
    if not os.path.exists(TELEMETRY_DIR):
        return []

    files = [os.path.join(TELEMETRY_DIR, f) for f in os.listdir(TELEMETRY_DIR) if f.endswith(".ptn")]

    # Deterministic mode: avoid filesystem mtime ordering (unstable across runs)
    if _deterministic_time_enabled():
        files = sorted(files, reverse=True)  # assumes filenames contain timestamps (common)
        return files[:limit]

    files = sorted(files, key=os.path.getmtime, reverse=True)
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

    # Recorder shape: data["state"] may contain nested "resonance"
    resonance = (data.get("state", {}) or {}).get("resonance", {}) or {}
    seq = str(resonance.get("seq", ""))
    intensity = float(resonance.get("intensity", 1.0) or 1.0)

    # Support both "container" and "container_id" keys (older/newer writers)
    container_id = str(data.get("container") or data.get("container_id") or container_id)

    QuantumFieldCanvas = _get_quantum_field_canvas_cls()
    qfc = QuantumFieldCanvas()
    replay_state = qfc.resonate(seq, intensity=float(intensity), container_id=container_id)

    sqi = _compute_sqi_optimize()
    qqc = _emit_qqc(float(intensity))

    # Reinjection layer - rehydrate SCI and container state (optional)
    if reinject:
        try:
            SCIWorkspace, load_container_workspace = _reinjection_modules()
            load_container_workspace(container_id, state=data.get("state", {}))
            sci_ws = SCIWorkspace(container_id)
            sci_ws.inject_state(data.get("state", {}))
            if not _quiet_enabled():
                print(f"♻️ Reinjected workspace for [{container_id}] from {os.path.basename(path)}")
        except Exception as e:
            if not _quiet_enabled():
                print(f"⚠️ Reinjection failed for {path}: {e}")

    frame = {
        "timestamp": _now_iso(),
        "seq": seq,
        "intensity": float(intensity),
        "sqi_feedback": sqi,
        "qqc_feedback": qqc,
        "replayed_state": replay_state,
        "replayed_from": os.path.basename(path),
        "container_id": container_id,
    }

    if broadcast:
        try:
            await _trigger_qfc_render(
                {"type": "timeline_frame", "frame": frame, "label": "photon_replay"},
                source="timeline_replay",
            )
            if not _quiet_enabled():
                print(f"🌀 QFC frame broadcasted: {path}")
        except Exception as e:
            if not _quiet_enabled():
                print(f"⚠️ Failed to broadcast replay frame: {e}")

    if delay > 0:
        await asyncio.sleep(float(delay))

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
        if not _quiet_enabled():
            print("⚠️ No saved resonance telemetry snapshots found.")
        return []

    snapshots.reverse()  # old -> new (given list_available_snapshots returns newest-first)
    frames: List[Dict[str, Any]] = []
    if not _quiet_enabled():
        print(f"🎞️ Replaying {len(snapshots)} frames (reinjection={'on' if reinject else 'off'})...")

    for p in snapshots:
        frames.append(
            await replay_snapshot(
                p,
                broadcast=broadcast,
                delay=delay,
                reinject=reinject,
                container_id=container_id,
            )
        )

    if not _quiet_enabled():
        print("✅ Timeline replay complete.")
    return frames
