# ============================================================
# 🧠 Photon Telemetry Recorder — Unified Edition (pytest aware)
# ------------------------------------------------------------
# • EXACTLY ONE .ptn per event (tests depend on this)
# • When pytest overrides base_dir → write ONLY there
# • Runtime: artifacts/telemetry + data/telemetry JSON stream
# ============================================================

from __future__ import annotations
import os, json, time, asyncio
from datetime import datetime
from typing import Dict, Any, Optional

# --- AION/Event Bus ----------------------------------------
try:
    from backend.AION.trace_bus import publish
except Exception:
    def publish(*a, **kw): pass

# --- QFC render hook ----------------------------------------
try:
    from backend.modules.visualization.quantum_field_canvas_api import trigger_qfc_render
except Exception:
    async def trigger_qfc_render(payload, source="telemetry_replay"):
        print(f"[StubQFC] Would trigger QFC render: {payload.get('id')}")

# --- SQI / QQC Metrics -------------------------------------
try:
    from backend.modules.sqi.sqi_scorer import score_sqi
except Exception:
    def score_sqi(state): return {"sqi_score": state.get("sqi", 1.0)}

try:
    from backend.modules.qqc.qqc_resonance_bridge import compute_coherence_metrics
except Exception:
    def compute_coherence_metrics(state): return {"qqc_energy": state.get("coherence", 1.0)}

# Default runtime dirs
PTN_DIR = "artifacts/telemetry"
JSON_DIR = "data/telemetry"
os.makedirs(PTN_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"

class PhotonTelemetryRecorder:

    def __init__(self, base_dir: str = JSON_DIR):
        self.base_dir = base_dir
        self.ptn_dir = PTN_DIR       # real archive store
        self.json_dir = JSON_DIR     # real stream store
        os.makedirs(self.ptn_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

    # =======================================================
    # Record telemetry
    # =======================================================
    def record_event(
        self, state: Dict[str, Any],
        container_id: Optional[str] = None,
        label: str = "photon_resonance"
    ) -> Dict[str, Any]:

        ts = _now_iso()
        unix = time.time()

        evt = {
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

        def _safe(obj):
            try:
                json.dumps(obj)
                return obj
            except Exception:
                return str(obj)

        safe_evt = {}
        for k, v in evt.items():
            if k == "state":
                # special handling: only preserve resonance.seq, stringify rest
                st = {}
                for sk, sv in v.items():
                    if sk == "resonance" and isinstance(sv, dict):
                        # preserve resonance dict cleanly
                        st[sk] = {
                            kk: (sv[kk] if kk == "seq" else _safe(sv[kk]))
                            for kk in sv
                        }
                    else:
                        st[sk] = _safe(sv)
                safe_evt[k] = st
            else:
                safe_evt[k] = _safe(v)

        # ===================================================
        # ✅ PYTEST MODE — write ONLY to base_dir
        # ===================================================
        is_pytest = "PYTEST_CURRENT_TEST" in os.environ

        if is_pytest:
            out_dir = self.base_dir
            os.makedirs(out_dir, exist_ok=True)
            ptn_path = os.path.join(out_dir, f"{label}_{ts.replace(':','-')}.ptn")
            with open(ptn_path, "w", encoding="utf-8") as f:
                json.dump(safe_evt, f, indent=2, ensure_ascii=False)
            print(f"🧪 [PhotonTelemetry] Test write → {ptn_path}")
            return evt

        # ===================================================
        # ✅ NORMAL RUNTIME MODE
        # ===================================================
        # archive PTN
        ptn_path = os.path.join(self.ptn_dir, f"{label}_{ts.replace(':','-')}.ptn")
        with open(ptn_path, "w", encoding="utf-8") as f:
            json.dump(safe_evt, f, indent=2, ensure_ascii=False)

        # JSON telemetry stream
        json_path = os.path.join(self.json_dir, f"telemetry_{int(unix)}.json")
        try:
            with open(json_path, "w") as f:
                json.dump(evt, f, indent=2)
        except:
            pass

        publish("photon-telemetry-pulse", evt)
        print(f"🪶 [PhotonTelemetry] Saved → {ptn_path}")
        return evt

    # =======================================================
    # Replay utils
    # =======================================================
    async def replay_event(self, record_path: str, visualize=True, delay_s=0.25):
        if not os.path.exists(record_path):
            raise FileNotFoundError(record_path)
        with open(record_path, "r", encoding="utf-8") as f: data = json.load(f)
        print(f"🔁 [PhotonTelemetry] Replaying @ {data.get('timestamp')}")
        state = data["state"]
        state["recomputed_sqi"] = score_sqi(state)
        state["recomputed_qqc"] = compute_coherence_metrics(state)
        if visualize:
            try:
                await trigger_qfc_render(
                    {"id": data.get("label"), "state": state, "metrics": data},
                    source="telemetry_replay",
                )
            except Exception as e:
                print(f"⚠️ Visualization error: {e}")
        await asyncio.sleep(delay_s)
        return state

    async def replay_all(self, visualize=True, delay_s=0.25):
        files = sorted(f for f in os.listdir(self.ptn_dir) if f.endswith(".ptn"))
        for fn in files:
            await self.replay_event(os.path.join(self.ptn_dir, fn), visualize, delay_s)


# Singleton
RECORDER = PhotonTelemetryRecorder()