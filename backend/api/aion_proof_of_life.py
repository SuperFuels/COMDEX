from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query

router = APIRouter(tags=["AION Proof Of Life"])

# ============================================================
# data-root (robust, but still simple)
# ============================================================
ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"


def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def pick_data_root() -> Path:
    # 1) explicit override
    raw = (os.getenv(ENV_DATA_ROOT) or "").strip()
    if raw:
        return Path(raw).expanduser()

    # 2) runtime moved data (most common in your logs)
    rt = Path(".runtime")
    if rt.exists():
        cands = sorted(
            rt.glob("*/data"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
        )
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
    """
    Read the last JSON object from a JSONL (or log) file.
    Works even if the file has occasional non-JSON lines.
    """
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


# ============================================================
# Φ (metabolism)
# ============================================================
def _phi_path_candidates() -> list[Path]:
    # tolerate historical "data/data/*" mishaps
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
    # keep same semantics: write memory then reinforce
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


# ============================================================
# ADR (immune / drift repair) — REAL FILES + REAL ACTIONS
# ============================================================
RESONANCE_STREAM_PATH = DATA_ROOT / "feedback" / "resonance_stream.jsonl"
DRIFT_REPAIR_LOG_PATH = DATA_ROOT / "feedback" / "drift_repair.log"
PAL_STATE_PATH = DATA_ROOT / "prediction" / "pal_state.json"


def _ensure_adr_files() -> None:
    RESONANCE_STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    DRIFT_REPAIR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not RESONANCE_STREAM_PATH.exists():
        RESONANCE_STREAM_PATH.write_text("", encoding="utf-8")
    if not DRIFT_REPAIR_LOG_PATH.exists():
        DRIFT_REPAIR_LOG_PATH.write_text("", encoding="utf-8")
    if not PAL_STATE_PATH.exists():
        _write_json(
            PAL_STATE_PATH,
            {
                "ts": time.time(),
                "epsilon": 0.15,
                "k": 8,
                "memory_weight": 0.50,
                "reason": "ADR_INIT",
            },
        )


def _float_or_none(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _int_or_none(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def _derive_zone(rsi: Optional[float]) -> str:
    if rsi is None:
        return "UNKNOWN"
    if rsi >= 0.95:
        return "GREEN"
    if rsi >= 0.60:
        return "YELLOW"
    return "RED"


def adr_state() -> Dict[str, Any]:
    _ensure_adr_files()

    evt = _read_last_jsonl(RESONANCE_STREAM_PATH) or {}
    drift = _read_last_jsonl(DRIFT_REPAIR_LOG_PATH)  # may be None
    pal = _read_json(PAL_STATE_PATH, default={}) or {}

    # RSI comes from stream event
    rsi = _float_or_none(evt.get("RSI"))
    if rsi is None:
        rsi = _float_or_none(evt.get("stability"))

    zone = _derive_zone(rsi)

    # trigger/pulse comes from drift log timestamps if present
    status = "ARMED"
    red_pulse = False
    last_trigger_age_s: Optional[float] = None

    # Support multiple drift event schemas
    drift_ts = None
    if isinstance(drift, dict):
        drift_ts = drift.get("timestamp") or drift.get("ts")
    drift_ts_f = _float_or_none(drift_ts)

    if drift_ts_f is not None:
        last_trigger_age_s = max(0.0, time.time() - drift_ts_f)
        red_pulse = last_trigger_age_s <= 0.75
        status = "TRIGGERED" if red_pulse else "RECOVERING"
    else:
        # fall back to PAL "reason" if it looks like ADR recently ran
        reason = str(pal.get("reason", "") or "")
        if reason.upper().startswith("ADR"):
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
        "latest_drift_repair": drift if drift else None,
        "pal_state": pal,
        "derived": {
            "rsi": rsi,
            "zone": zone,
            "adr_status": status,
            "red_pulse": red_pulse,
            "last_trigger_age_s": last_trigger_age_s,
        },
    }


@router.get("/api/adr")
def api_adr() -> Dict[str, Any]:
    return adr_state()


# --- REAL ACTION: inject drift (writes drift log + optionally stream event)
@router.post("/api/adr/inject")
def api_adr_inject(
    amount: float = Body(0.25),
    write_stream_event: bool = Body(True),
) -> Dict[str, Any]:
    _ensure_adr_files()

    now = time.time()
    drift_evt = {
        "timestamp": now,
        "type": "inject_drift",
        "amount": float(amount),
        "source": "proof_of_life",
    }
    with open(DRIFT_REPAIR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(drift_evt, ensure_ascii=False) + "\n")

    if write_stream_event:
        # push an RSI-ish stream event so the dashboard immediately reflects a red/yellow shift
        stream_evt = {
            "timestamp": now,
            "stability": max(0.0, min(1.0, 0.60 - float(amount))),
            "drift_entropy": max(0.0, min(1.0, 0.40 + float(amount))),
            "source": "proof_of_life",
        }
        with open(RESONANCE_STREAM_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(stream_evt, ensure_ascii=False) + "\n")

    return {"ok": True, "action": "adr_inject", "event": drift_evt, **adr_state()}


# --- REAL ACTION: run ADR (PAL once) + ensure pal_state exists
@router.post("/api/adr/run")
def api_adr_run(
    epsilon: Optional[float] = Body(None),
    k: Optional[int] = Body(None),
    memory_weight: Optional[float] = Body(None),
    mode: str = Body("resonance-feedback"),
) -> Dict[str, Any]:
    """
    Runs PAL in the same way your stack already does, then makes sure pal_state.json
    has epsilon/k/memory_weight populated so the UI never shows "—".
    """
    _ensure_adr_files()

    before = _read_json(PAL_STATE_PATH, default={}) or {}

    # Run PAL (best-effort)
    cmd = [sys.executable, "backend/modules/aion_perception/pal_core.py", f"--mode={mode}"]
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", ".") or "."
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=45)

    # Update pal_state.json with either provided overrides or a conservative adjustment
    after = dict(before)

    # prefer explicit values from request
    if epsilon is not None:
        after["epsilon"] = float(epsilon)
    else:
        # small tightening (less exploration) as a default "repair"
        eps0 = _float_or_none(before.get("epsilon")) or 0.15
        after["epsilon"] = max(0.01, min(1.0, eps0 * 0.90))

    if k is not None:
        after["k"] = int(k)
    else:
        k0 = _int_or_none(before.get("k")) or 8
        after["k"] = max(1, min(64, k0))

    if memory_weight is not None:
        after["memory_weight"] = float(memory_weight)
    else:
        mw0 = _float_or_none(before.get("memory_weight")) or 0.50
        after["memory_weight"] = max(0.05, min(0.95, mw0 + 0.05))

    after["ts"] = time.time()
    after["reason"] = "ADR_RUN"
    _write_json(PAL_STATE_PATH, after)

    proof = {
        "timestamp": time.time(),
        "type": "adr_repair",
        "before": {
            "epsilon": before.get("epsilon"),
            "k": before.get("k"),
            "memory_weight": before.get("memory_weight"),
        },
        "after": {
            "epsilon": after.get("epsilon"),
            "k": after.get("k"),
            "memory_weight": after.get("memory_weight"),
        },
        "pal_returncode": r.returncode,
    }
    with open(DRIFT_REPAIR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(proof, ensure_ascii=False) + "\n")

    return {
        "ok": r.returncode == 0,
        "action": "adr_run",
        "returncode": r.returncode,
        "stdout_tail": (r.stdout or "").splitlines()[-20:],
        "stderr_tail": (r.stderr or "").splitlines()[-20:],
        "proof": proof,
        **adr_state(),
    }


# --- Backwards-compat (your old demo routes). Keep, but point to real actions.
@router.post("/api/demo/adr/inject")
def api_demo_adr_inject() -> Dict[str, Any]:
    return api_adr_inject(amount=0.25, write_stream_event=True)


@router.post("/api/demo/adr/run")
def api_demo_adr_run() -> Dict[str, Any]:
    return api_adr_run()


# ============================================================
# Reflex (demo 4)
# ============================================================
@router.get("/api/reflex")
def api_reflex() -> Dict[str, Any]:
    from backend.modules.aion_demo import reflex_grid as reflex_mod

    st = reflex_mod.get_state(DATA_ROOT / "grid_state.json")
    return {"ok": True, "data_root": str(DATA_ROOT), "state": st}


# ============================================================
# Homeostasis alias (so dashboard can call /api/homeostasis)
# ============================================================
@router.get("/api/homeostasis")
def api_homeostasis() -> Dict[str, Any]:
    snap = _read_json(Path("data/analysis/aion_live_dashboard.json"), default={}) or {}
    last = (snap.get("homeostasis", {}) or {}).get("last") or snap.get("last")
    return {
        "ok": True,
        "generated_at": snap.get("generated_at"),
        "events": snap.get("events"),
        "homeostasis": snap.get("homeostasis"),
        "last": last,
    }


# ============================================================
# Mirror (demo 6) – minimal “now” snapshot + last log file if present
# ============================================================
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

    freshness = 1.0 if (hb_age_ms is not None and hb_age_ms < 2000) else 0.6
    A = max(0.0, min(1.0, 0.55 * coh + 0.35 * (1.0 - ent) + 0.10 * freshness))

    frames = []
    session_id = f"DEMO6-{int(time.time())}"
    for t in range(int(steps)):
        narration = f"[{session_id}] MIRROR t={t:02d} | coh={coh:.3f} ent={ent:.3f} Θ_age={hb_age_ms}ms | A={A:.3f}"
        frames.append(
            {
                "t": t,
                "A": A,
                "phi": phiS,
                "heartbeat_age_ms": hb_age_ms,
                "narration": narration,
            }
        )

    MIRROR_QDATA.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "demo": "demo6_mirror_reflection",
        "session_id": session_id,
        "steps": int(steps),
        "frames": frames,
        "A_final": A,
    }
    _write_json(MIRROR_QDATA, out)
    return {"ok": True, **out}


# ============================================================
# optional: “breathing tick” (very small) – controlled by env
# ============================================================
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
        await asyncio.sleep(float(os.getenv("AION_DEMO_PHI_BREATHE_S", "0.75")))


@router.on_event("startup")
async def _startup_tasks() -> None:
    asyncio.create_task(_phi_breathe_loop())