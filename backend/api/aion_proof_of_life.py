from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

router = APIRouter(tags=["AION Proof Of Life"])

# -----------------------------
# data-root (keep simple)
# -----------------------------
ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}

def pick_data_root() -> Path:
    # 1) explicit override
    raw = os.getenv(ENV_DATA_ROOT, "").strip()
    if raw:
        return Path(raw).expanduser()

    # 2) runtime moved data (most common in your logs)
    rt = Path(".runtime")
    if rt.exists():
        cands = sorted(rt.glob("*/data"), key=lambda p: p.stat().st_mtime if p.exists() else 0.0)
        if cands:
            return cands[-1]

    # 3) fallback
    return Path("data")

DATA_ROOT = pick_data_root()

def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def _read_last_jsonl(path: Path, max_bytes: int = 65536) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes), 0)
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        for line in reversed(lines):
            try:
                return json.loads(line)
            except Exception:
                continue
        return None
    except Exception:
        return None

def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _age_s(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds()

# -----------------------------
# Φ (metabolism)
# -----------------------------
def _phi_path_candidates() -> list[Path]:
    # you currently have a double data/ in at least one place; tolerate it
    return [
        DATA_ROOT / "phi_reinforce_state.json",
        DATA_ROOT / "data" / "phi_reinforce_state.json",
        Path("data") / "phi_reinforce_state.json",
        Path("data") / "data" / "phi_reinforce_state.json",
    ]

def phi_state() -> Dict[str, Any]:
    src = None
    st = None
    for p in _phi_path_candidates():
        j = _read_json(p, default=None)
        if isinstance(j, dict) and j:
            src, st = p, j
            break
    st = st or {}
    last = st.get("last_update")
    dt = _parse_iso(last) if isinstance(last, str) else None
    age = _age_s(dt)
    pulse_active = (age is not None) and (age <= 30.0)

    return {
        "ok": bool(st),
        "data_root": str(DATA_ROOT),
        "source_file": str(src) if src else None,
        "state": st,
        "derived": {
            "last_update_iso": last,
            "last_update_age_s": age,
            "metabolic_pulse": "ACTIVE" if pulse_active else "AT_REST",
        },
    }

@router.get("/api/phi")
def api_phi() -> Dict[str, Any]:
    return phi_state()

@router.post("/api/demo/phi/reset")
def api_phi_reset() -> Dict[str, Any]:
    from backend.modules.aion_resonance.phi_reinforce import reset_reinforce_state
    reset_reinforce_state()
    return {"ok": True, "action": "reset", **phi_state()}

@router.post("/api/demo/phi/inject_entropy")
def api_phi_inject_entropy() -> Dict[str, Any]:
    # keep same semantics you had: write memory then reinforce
    from backend.modules.aion_resonance.phi_reinforce import reinforce_from_memory

    mem_path = DATA_ROOT / "conversation_memory.json"
    mem_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"phi": {"Φ_coherence": 0.10, "Φ_entropy": 0.90}}]
    _write_json(mem_path, payload)

    out = reinforce_from_memory()
    return {"ok": True, "action": "inject_entropy", "result": out, **phi_state()}

@router.post("/api/demo/phi/recover")
def api_phi_recover() -> Dict[str, Any]:
    from backend.modules.aion_resonance.phi_reinforce import update_beliefs

    mem_path = DATA_ROOT / "conversation_memory.json"
    mem_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(mem_path, [])

    out = update_beliefs({})
    return {"ok": True, "action": "recover", "result": out, **phi_state()}

# -----------------------------
# ADR (immune / drift repair)
# -----------------------------
RESONANCE_STREAM_PATH = DATA_ROOT / "feedback" / "resonance_stream.jsonl"
DRIFT_REPAIR_LOG_PATH = DATA_ROOT / "feedback" / "drift_repair.log"
PAL_STATE_PATH = DATA_ROOT / "prediction" / "pal_state.json"

def adr_state() -> Dict[str, Any]:
    evt = _read_last_jsonl(RESONANCE_STREAM_PATH) or {}
    drift = _read_last_jsonl(DRIFT_REPAIR_LOG_PATH) or None
    pal = _read_json(PAL_STATE_PATH, default={}) or {}

    rsi = None
    if "RSI" in evt:
        try: rsi = float(evt.get("RSI"))
        except Exception: rsi = None
    if rsi is None and "stability" in evt:
        try: rsi = float(evt.get("stability"))
        except Exception: rsi = None

    zone = "UNKNOWN"
    if rsi is not None:
        if rsi >= 0.95: zone = "GREEN"
        elif rsi >= 0.60: zone = "YELLOW"
        else: zone = "RED"

    status = "ARMED"
    pulse = False
    last_trigger_age_s = None
    if isinstance(drift, dict) and "timestamp" in drift:
        try:
            ts = float(drift["timestamp"])
            last_trigger_age_s = time.time() - ts
            pulse = last_trigger_age_s <= 0.75
        except Exception:
            pass

    if drift:
        status = "TRIGGERED" if pulse else "RECOVERING"
    elif str(pal.get("reason", "")).upper().startswith("ADR"):
        status = "RECOVERING"

    return {
        "ok": True,
        "data_root": str(DATA_ROOT),
        "source_files": {
            "resonance_stream": str(RESONANCE_STREAM_PATH),
            "drift_repair_log": str(DRIFT_REPAIR_LOG_PATH),
            "pal_state": str(PAL_STATE_PATH),
        },
        "latest_stream_event": evt if evt else None,
        "latest_drift_repair": drift,
        "pal_state": pal,
        "derived": {
            "rsi": rsi,
            "zone": zone,
            "adr_status": status,
            "red_pulse": pulse,
            "last_trigger_age_s": last_trigger_age_s,
        },
    }

@router.get("/api/adr")
def api_adr() -> Dict[str, Any]:
    return adr_state()

@router.post("/api/demo/adr/inject")
def api_adr_inject() -> Dict[str, Any]:
    RESONANCE_STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    evt = {
        "timestamp": time.time(),
        "stability": 0.45,
        "drift_entropy": 0.92,
        "source": "proof_of_life",
    }
    with open(RESONANCE_STREAM_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    return {"ok": True, "action": "adr_inject", "event": evt, **adr_state()}

@router.post("/api/demo/adr/run")
def api_adr_run() -> Dict[str, Any]:
    # exactly what you already do elsewhere: run PAL once
    import subprocess, sys
    cmd = [sys.executable, "backend/modules/aion_perception/pal_core.py", "--mode=resonance-feedback"]
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", ".") or "."
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=45)
    return {
        "ok": r.returncode == 0,
        "action": "adr_run",
        "returncode": r.returncode,
        "stdout_tail": (r.stdout or "").splitlines()[-20:],
        "stderr_tail": (r.stderr or "").splitlines()[-20:],
        **adr_state(),
    }

# -----------------------------
# Reflex (demo 4)
# -----------------------------
@router.get("/api/reflex")
def api_reflex() -> Dict[str, Any]:
    from backend.modules.aion_demo import reflex_grid as reflex_mod
    st = reflex_mod.get_state(DATA_ROOT / "grid_state.json")
    return {"ok": True, "data_root": str(DATA_ROOT), "state": st}

# -----------------------------
# Homeostasis alias (so dashboard can call /api/homeostasis)
# -----------------------------
@router.get("/api/homeostasis")
def api_homeostasis() -> Dict[str, Any]:
    # read the same snapshot your existing dashboard reads
    snap = _read_json(Path("data/analysis/aion_live_dashboard.json"), default={}) or {}
    last = (snap.get("homeostasis", {}) or {}).get("last") or snap.get("last")
    return {
        "ok": True,
        "generated_at": snap.get("generated_at"),
        "events": snap.get("events"),
        "homeostasis": snap.get("homeostasis"),
        "last": last,
    }

# -----------------------------
# Mirror (demo 6) – minimal “now” snapshot + last log file if present
# -----------------------------
MIRROR_QDATA = DATA_ROOT / "telemetry" / "demo6_mirror_reflection.qdata.json"

@router.get("/api/mirror")
def api_mirror() -> Dict[str, Any]:
    j = _read_json(MIRROR_QDATA, default=None)
    return {
        "ok": bool(j),
        "data_root": str(DATA_ROOT),
        "source_file": str(MIRROR_QDATA),
        "state": j,
    }

@router.post("/api/demo/mirror/run")
def api_mirror_run(steps: int = 12) -> Dict[str, Any]:
    # run a tiny “mirror” snapshot generator using real phi + heartbeat
    phi = phi_state()
    hb = _read_json(DATA_ROOT / "aion_field" / "global_theta_heartbeat_live.json", default={}) or {}

    phiS = phi.get("state", {}) or {}
    coh = float(phiS.get("Φ_coherence", 0.5) or 0.5)
    ent = float(phiS.get("Φ_entropy", 0.5) or 0.5)
    hb_age_ms = None
    try:
        ts = float(hb.get("timestamp"))
        hb_age_ms = int((time.time() - ts) * 1000)
    except Exception:
        pass

    # simple alignment A: higher coherence + lower entropy + fresh heartbeat
    freshness = 1.0 if (hb_age_ms is not None and hb_age_ms < 2000) else 0.6
    A = max(0.0, min(1.0, 0.55 * coh + 0.35 * (1.0 - ent) + 0.10 * freshness))

    frames = []
    session_id = f"DEMO6-{int(time.time())}"
    for t in range(int(steps)):
        narration = f"[{session_id}] MIRROR t={t:02d} | coh={coh:.3f} ent={ent:.3f} Θ_age={hb_age_ms}ms | A={A:.3f}"
        frames.append({"t": t, "A": A, "phi": phiS, "heartbeat_age_ms": hb_age_ms, "narration": narration})

    MIRROR_QDATA.parent.mkdir(parents=True, exist_ok=True)
    out = {"demo": "demo6_mirror_reflection", "session_id": session_id, "steps": int(steps), "frames": frames, "A_final": A}
    _write_json(MIRROR_QDATA, out)
    return {"ok": True, **out}

# -----------------------------
# optional: “breathing tick” (very small) – controlled by env
# -----------------------------
async def _phi_breathe_loop() -> None:
    if not _truthy("AION_DEMO_PHI_BREATHE", False):
        return
    try:
        from backend.modules.aion_resonance.phi_reinforce import breathe_tick
    except Exception:
        return

    while True:
        try:
            breathe_tick()
        except Exception:
            pass
        await asyncio.sleep(0.75)

@router.on_event("startup")
async def _startup_tasks() -> None:
    # lightweight background “breathing”
    asyncio.create_task(_phi_breathe_loop())