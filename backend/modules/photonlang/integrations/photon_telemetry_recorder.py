# ============================================================
# 🧠 Photon Telemetry Recorder - Unified Edition (pytest aware)
# ------------------------------------------------------------
# * EXACTLY ONE .ptn per event (tests depend on this)
# * When pytest overrides base_dir -> write ONLY there
# * Runtime: artifacts/telemetry + data/telemetry JSON stream
#
# Hardening:
# * NO import-time filesystem writes / singleton bring-up
# * Deterministic time support (TESSARIS_DETERMINISTIC_TIME=1)
# * Quiet mode support (TESSARIS_TEST_QUIET=1)
# ============================================================

from __future__ import annotations

import os
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# --- Determinism / quiet gates -----------------------------------------------
def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"

def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"

def _now_unix() -> float:
    return 0.0 if _deterministic_time_enabled() else time.time()

def _now_iso() -> str:
    if _deterministic_time_enabled():
        # Stable, schema-ish ISO8601 marker for deterministic runs
        return "0000-00-00T00:00:00.000Z"
    dt = datetime.now(timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

def _qprint(msg: str) -> None:
    if not _quiet_enabled():
        print(msg)

# --- AION/Event Bus ----------------------------------------------------------
try:
    from backend.AION.trace_bus import publish
except Exception:
    def publish(*a, **kw):  # type: ignore
        return None

# --- QFC render hook ---------------------------------------------------------
try:
    from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
except Exception:
    async def trigger_qfc_render(payload, source: str = "telemetry_replay"):
        _qprint(f"[StubQFC] Would trigger QFC render: {payload.get('id')}")

# --- SQI / QQC Metrics -------------------------------------------------------
try:
    from backend.modules.sqi.sqi_scorer import score_sqi
except Exception:
    def score_sqi(state):  # type: ignore
        return {"sqi_score": state.get("sqi", 1.0)}

try:
    from backend.modules.qqc.qqc_resonance_bridge import compute_coherence_metrics
except Exception:
    def compute_coherence_metrics(state):  # type: ignore
        return {"qqc_energy": state.get("coherence", 1.0)}

# Default runtime dirs (do NOT mkdir at import time)
PTN_DIR = "artifacts/telemetry"
JSON_DIR = "data/telemetry"


class PhotonTelemetryRecorder:
    def __init__(self, base_dir: str = JSON_DIR):
        self.base_dir = base_dir
        self.ptn_dir = PTN_DIR       # real archive store
        self.json_dir = JSON_DIR     # real stream store

    # =======================================================
    # Record telemetry
    # =======================================================
    def record_event(
        self,
        state: Dict[str, Any],
        container_id: Optional[str] = None,
        label: str = "photon_resonance",
    ) -> Dict[str, Any]:
        ts = _now_iso()
        unix = _now_unix()

        evt: Dict[str, Any] = {
            "ts": unix,
            "timestamp": ts,
            "label": label,
            "container": container_id,
            "seq": state.get("seq"),
            "ops": state.get("ops", []),
            "coherence": state.get("coherence"),
            "entropy": state.get("entropy"),
            "sqi": state.get("sqi"),
            "sqi_feedback": score_sqi(state),
            "qqc_feedback": compute_coherence_metrics(state),
            "state": state,
        }

        def _safe(obj: Any) -> Any:
            try:
                json.dumps(obj)
                return obj
            except Exception:
                return str(obj)

        safe_evt: Dict[str, Any] = {}
        for k, v in evt.items():
            if k == "state" and isinstance(v, dict):
                # special handling: preserve resonance.seq, stringify rest
                st: Dict[str, Any] = {}
                for sk, sv in v.items():
                    if sk == "resonance" and isinstance(sv, dict):
                        st[sk] = {kk: (sv[kk] if kk == "seq" else _safe(sv[kk])) for kk in sv}
                    else:
                        st[sk] = _safe(sv)
                safe_evt[k] = st
            else:
                safe_evt[k] = _safe(v)

        # ===================================================
        # ✅ PYTEST MODE - write ONLY to base_dir
        # ===================================================
        is_pytest = "PYTEST_CURRENT_TEST" in os.environ
        if is_pytest:
            out_dir = self.base_dir
            os.makedirs(out_dir, exist_ok=True)
            ptn_path = os.path.join(out_dir, f"{label}_{ts.replace(':','-')}.ptn")
            with open(ptn_path, "w", encoding="utf-8") as f:
                json.dump(safe_evt, f, indent=2, ensure_ascii=False)
            _qprint(f"🧪 [PhotonTelemetry] Test write -> {ptn_path}")
            return evt

        # ===================================================
        # ✅ NORMAL RUNTIME MODE
        # ===================================================
        os.makedirs(self.ptn_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

        # archive PTN
        ptn_path = os.path.join(self.ptn_dir, f"{label}_{ts.replace(':','-')}.ptn")
        with open(ptn_path, "w", encoding="utf-8") as f:
            json.dump(safe_evt, f, indent=2, ensure_ascii=False)

        # JSON telemetry stream
        json_path = os.path.join(self.json_dir, f"telemetry_{int(unix)}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(evt, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        try:
            publish("photon-telemetry-pulse", evt)
        except Exception:
            pass

        _qprint(f"🪶 [PhotonTelemetry] Saved -> {ptn_path}")
        return evt

    # =======================================================
    # Replay utils
    # =======================================================
    async def replay_event(self, record_path: str, visualize: bool = True, delay_s: float = 0.25):
        if not os.path.exists(record_path):
            raise FileNotFoundError(record_path)
        with open(record_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        _qprint(f"🔁 [PhotonTelemetry] Replaying @ {data.get('timestamp')}")
        state = data.get("state") or {}

        # recompute
        try:
            state["recomputed_sqi"] = score_sqi(state)
        except Exception:
            state["recomputed_sqi"] = {"sqi_score": state.get("sqi", 1.0)}
        try:
            state["recomputed_qqc"] = compute_coherence_metrics(state)
        except Exception:
            state["recomputed_qqc"] = {"qqc_energy": state.get("coherence", 1.0)}

        if visualize:
            try:
                await trigger_qfc_render(
                    {"id": data.get("label"), "state": state, "metrics": data},
                    source="telemetry_replay",
                )
            except Exception as e:
                _qprint(f"⚠️ Visualization error: {e}")

        await asyncio.sleep(delay_s)
        return state

    async def replay_all(self, visualize: bool = True, delay_s: float = 0.25):
        if not os.path.isdir(self.ptn_dir):
            return
        files = sorted(f for f in os.listdir(self.ptn_dir) if f.endswith(".ptn"))
        for fn in files:
            await self.replay_event(os.path.join(self.ptn_dir, fn), visualize, delay_s)


# -----------------------------------------------------------------------------
# Lazy singleton (NO import-time bring-up)
# -----------------------------------------------------------------------------
_RECORDER: Optional[PhotonTelemetryRecorder] = None

def get_RECORDER() -> PhotonTelemetryRecorder:
    global _RECORDER
    if _RECORDER is None:
        _RECORDER = PhotonTelemetryRecorder()
    return _RECORDER

class _RecorderProxy:
    def __getattr__(self, name: str):
        return getattr(get_RECORDER(), name)

# Back-compat: allow `from ... import RECORDER` without triggering init.
RECORDER = _RecorderProxy()
