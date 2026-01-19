#!/usr/bin/env python3
"""
AION Demo Bridge (FastAPI)
────────────────────────────────────────────────────────────────
Purpose:
- Provide a single, stable backend surface for the frontend "Proof of Life" dashboard.
- Avoid tailing multiple files inside React; the bridge reads canonical state files
  and exposes them as JSON endpoints + websocket streaming.

Endpoints:
- GET  /health

Metabolism (Φ):
- GET  /api/phi
- POST /api/demo/phi/reset
- POST /api/demo/phi/inject_entropy
- POST /api/demo/phi/recover

Immune Response (ADR):
- GET  /api/adr
- POST /api/demo/adr/inject
- POST /api/demo/adr/run

Heartbeat / Persistent Presence (Demo 3):
- GET  /api/heartbeat
    Optional query:
      ?namespace=demo            -> prefer <DATA_ROOT>/aion_field/demo_heartbeat_live.json
      ?namespace=state_manager   -> prefer <DATA_ROOT>/aion_field/state_manager_heartbeat_live.json

Compat (old one-button demo):
- POST /api/demo/inject_entropy   (runs: phi inject + adr inject + adr run)

Websocket:
- WS   /ws/aion-demo  (pushes {phi, adr, heartbeat, ts} periodically)

Files (source of truth; resolved via MRTC-aligned data-root discovery):
- <DATA_ROOT>/phi_reinforce_state.json
- <DATA_ROOT>/conversation_memory.json
- <DATA_ROOT>/feedback/resonance_stream.jsonl
- <DATA_ROOT>/feedback/drift_repair.log        (JSONL records)
- <DATA_ROOT>/prediction/pal_state.json
- <DATA_ROOT>/aion_field/resonant_heartbeat.jsonl   (preferred, if present)
- <DATA_ROOT>/aion_field/*heartbeat_live.json       (fallback)
- /tmp/aion_heartbeat_state.json                    (fallback)

Optional:
- If AION_DEMO_AUTOSTART_HEARTBEAT=1, the bridge will *attempt* to start
  resonance_heartbeat.py in the background (idempotent-ish via freshness check).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

# -----------------------------------------------------------------------------
# Repo root on sys.path so "backend...." imports work reliably (even when mounted)
# -----------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve()
# backend/modules/aion_demo/demo_bridge.py -> parents: demo_bridge.py, aion_demo, modules, backend, repo_root
for _p in _REPO_ROOT.parents:
    if (_p / "backend").exists():
        _REPO_ROOT = _p
        break
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.modules.aion_demo import reflex_grid as reflex_mod

# Reflex (Demo 4)
REFLEX_STATE_PATH = DATA_ROOT / "grid_state.json"


# -----------------------------------------------------------------------------
# Data-root discovery (MRTC-aligned)
# -----------------------------------------------------------------------------
ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

KNOWN_SENTINELS = [
    "control/aqci_log.jsonl",
    "control/rqfs_feedback.jsonl",
    "learning/fusion_state.jsonl",
    "aion_field/resonant_heartbeat.jsonl",
    "analysis/resonant_optimizer.jsonl",
    "analysis/state_resonance_log.jsonl",
]


def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def pick_data_root() -> Path:
    """
    Mirrors backend/modules/aion_integrity/meta_resonant_telemetry_consolidator.py.
    Tries:
      1) ENV override
      2) .runtime/*/data
      3) ./data
    Chooses best by sentinel hits + newest mtime.
    """
    # 1) explicit override
    if ENV_DATA_ROOT in os.environ:
        p = Path(os.environ[ENV_DATA_ROOT]).expanduser()
        if (p / "control").exists() or any((p / s).exists() for s in KNOWN_SENTINELS):
            return p

    # 2) prefer runtime-moved data if present
    candidates: List[Path] = []
    rt = Path(".runtime")
    if rt.exists():
        for d in rt.glob("*/data"):
            candidates.append(d)

    # 3) include local ./data
    candidates.append(Path("data"))

    def score(d: Path) -> Tuple[int, float]:
        hits = 0
        newest = 0.0
        for s in KNOWN_SENTINELS:
            f = d / s
            if f.exists():
                hits += 1
                try:
                    newest = max(newest, f.stat().st_mtime)
                except Exception:
                    pass
        return (hits, newest)

    best = None
    best_score = (-1, -1.0)
    for d in candidates:
        sc = score(d)
        if sc > best_score:
            best = d
            best_score = sc

    return best if best else Path("data")


def _ensure_local_data_points_to(root: Path) -> None:
    """
    Compatibility shim: many subsystems write to relative 'data/...'.
    If DATA_ROOT is a runtime-moved path, prefer making ./data a symlink to it.
    Safe: if ./data is a real dir already, we don't rewrite it.
    """
    try:
        local = Path("data")
        root = root.resolve()
        if root.name != "data":
            return

        # If local is a broken symlink, replace it.
        if local.is_symlink():
            try:
                local.resolve(strict=True)
                return  # valid symlink, keep
            except FileNotFoundError:
                local.unlink(missing_ok=True)

        # If local exists as a real directory/file, leave it alone.
        if local.exists():
            return

        local.parent.mkdir(parents=True, exist_ok=True)
        local.symlink_to(root)
    except Exception:
        pass


DATA_ROOT = pick_data_root()
_ensure_local_data_points_to(DATA_ROOT)

# -----------------------------------------------------------------------------
# Paths (relative to DATA_ROOT)
# -----------------------------------------------------------------------------
PHI_PATH = DATA_ROOT / "phi_reinforce_state.json"
MEMORY_PATH = DATA_ROOT / "conversation_memory.json"

RESONANCE_STREAM_PATH = DATA_ROOT / "feedback" / "resonance_stream.jsonl"
DRIFT_REPAIR_LOG_PATH = DATA_ROOT / "feedback" / "drift_repair.log"
PAL_STATE_PATH = DATA_ROOT / "prediction" / "pal_state.json"

HEARTBEAT_JSONL_PATH = DATA_ROOT / "aion_field" / "resonant_heartbeat.jsonl"
HEARTBEAT_DIR = DATA_ROOT / "aion_field"
SUPERVISOR_STATE_PATH = Path("/tmp/aion_heartbeat_state.json")

# Default heartbeat namespace preference (your dashboard “demo 3” usually wants demo)
DEFAULT_HEARTBEAT_NS = os.getenv("AION_DEMO_HEARTBEAT_NAMESPACE", "demo")

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
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
    Tail the last valid JSON object from a .jsonl file without reading the whole thing.
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _seconds_since(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    return (_utc_now() - dt).total_seconds()


# -----------------------------------------------------------------------------
# Domain: Φ (Metabolism)
# -----------------------------------------------------------------------------
def phi_state() -> Dict[str, Any]:
    state = _read_json(PHI_PATH, default={}) or {}
    last_update = state.get("last_update")
    dt = _parse_iso(last_update)
    age_s = _seconds_since(dt)
    pulse_active = (age_s is not None) and (age_s <= 2.0)

    return {
        "data_root": str(DATA_ROOT),
        "source_file": str(PHI_PATH),
        "state": state,
        "derived": {
            "last_update_iso": last_update,
            "last_update_age_s": age_s,
            "metabolic_pulse": "ACTIVE" if pulse_active else "AT_REST",
        },
    }


def phi_reset() -> Dict[str, Any]:
    # NOTE: underlying module writes to relative 'data/...'; our symlink shim keeps it aligned.
    from backend.modules.aion_resonance.phi_reinforce import reset_reinforce_state

    out = reset_reinforce_state()
    return {"ok": True, "action": "reset", "result": out, **phi_state()}


def phi_inject_entropy(coherence: float = 0.10, entropy: float = 0.90) -> Dict[str, Any]:
    """
    Stressor: poison conversation memory with high entropy and run reinforce_from_memory().
    Mirrors the CLI demo you already validated.
    """
    from backend.modules.aion_resonance.phi_reinforce import reinforce_from_memory

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"phi": {"Φ_coherence": float(coherence), "Φ_entropy": float(entropy)}}]
    _write_json(MEMORY_PATH, payload)
    out = reinforce_from_memory()
    return {"ok": True, "action": "inject_entropy", "memory_written": payload, "result": out, **phi_state()}


def phi_recover() -> Dict[str, Any]:
    """
    Recovery: clear memory, then apply belief decay (update_beliefs({})).
    """
    from backend.modules.aion_resonance.phi_reinforce import update_beliefs

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json(MEMORY_PATH, [])
    out = update_beliefs({})
    return {"ok": True, "action": "recover", "result": out, **phi_state()}


# -----------------------------------------------------------------------------
# Domain: ADR (Immune Response)
# -----------------------------------------------------------------------------
def adr_state() -> Dict[str, Any]:
    evt = _read_last_jsonl(RESONANCE_STREAM_PATH) or {}
    drift = _read_last_jsonl(DRIFT_REPAIR_LOG_PATH)  # JSONL record with pre/post
    pal = _read_json(PAL_STATE_PATH, default={}) or {}

    # RSI / stability (frontend uses: RSI ?? stability)
    rsi = None
    if "RSI" in evt:
        try:
            rsi = float(evt.get("RSI"))
        except Exception:
            rsi = None
    if rsi is None and "stability" in evt:
        try:
            rsi = float(evt.get("stability"))
        except Exception:
            rsi = None

    drift_entropy = None
    for k in ("drift_entropy", "entropy"):
        if k in evt:
            try:
                drift_entropy = float(evt.get(k))
            except Exception:
                drift_entropy = None
            break

    # Zone classification
    zone = "UNKNOWN"
    if rsi is not None:
        if rsi >= 0.95:
            zone = "GREEN"
        elif rsi >= 0.60:
            zone = "YELLOW"
        else:
            zone = "RED"

    # Status + red pulse
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

    trigger_id = None
    if drift:
        try:
            trigger_id = f'{drift.get("timestamp","")}-{drift.get("event","")}-{drift.get("source","")}'
        except Exception:
            trigger_id = None

    return {
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
            "drift_entropy": drift_entropy,
            "zone": zone,
            "adr_status": status,
            "red_pulse": pulse,
            "last_trigger_age_s": last_trigger_age_s,
            "trigger_id": trigger_id,
        },
    }


# -----------------------------------------------------------------------------
# Domain: Heartbeat (Persistent Presence)
# -----------------------------------------------------------------------------
def _pick_live_heartbeat_file(namespace: Optional[str]) -> Optional[Path]:
    """
    Pick a specific <ns>_heartbeat_live.json if namespace is set (or preferred),
    otherwise pick newest mtime in aion_field/.
    """
    if not HEARTBEAT_DIR.exists():
        return None

    # 0) explicit namespace wins
    if namespace:
        p = HEARTBEAT_DIR / f"{namespace}_heartbeat_live.json"
        return p if p.exists() else None

    # 1) prefer DEFAULT_HEARTBEAT_NS if that file exists
    p0 = HEARTBEAT_DIR / f"{DEFAULT_HEARTBEAT_NS}_heartbeat_live.json"
    if p0.exists():
        return p0

    # 2) fallback newest
    try:
        files = list(HEARTBEAT_DIR.glob("*heartbeat_live.json"))
        if not files:
            return None
        files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0.0)
        return files[-1]
    except Exception:
        return None


def heartbeat_state(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns the latest heartbeat snapshot with a consistent envelope.

    If `namespace` is provided, we try HARD to return that namespace first.

    Preference order:
      1) <DATA_ROOT>/aion_field/resonant_heartbeat.jsonl (last JSONL entry)  [only if matching namespace or namespace not requested]
      2) <DATA_ROOT>/aion_field/<namespace>_heartbeat_live.json              [exact match]
      3) <DATA_ROOT>/aion_field/*heartbeat_live.json (newest mtime)         [fallback]
      4) /tmp/aion_heartbeat_state.json                                     [fallback]
    """
    now_s = time.time()
    ns = (namespace or "").strip() or None

    hb: Optional[dict] = None
    source: Optional[Path] = None

    # 1) jsonl heartbeat (only useful if it includes namespace, otherwise we can't target)
    j = _read_last_jsonl(HEARTBEAT_JSONL_PATH)
    if isinstance(j, dict):
        if ns is None or str(j.get("namespace", "")).strip() == ns:
            hb = j
            source = HEARTBEAT_JSONL_PATH

    # 2) exact live json snapshot by namespace
    if hb is None and ns and HEARTBEAT_DIR.exists():
        p = HEARTBEAT_DIR / f"{ns}_heartbeat_live.json"
        j = _read_json(p, default=None)
        if isinstance(j, dict):
            hb = j
            source = p

    # 3) fallback: newest live snapshot
    if hb is None and HEARTBEAT_DIR.exists():
        try:
            files = list(HEARTBEAT_DIR.glob("*heartbeat_live.json"))
            if files:
                files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0.0)
                p = files[-1]
                j = _read_json(p, default=None)
                if isinstance(j, dict):
                    hb = j
                    source = p
        except Exception:
            pass

    # 4) supervisor state fallback
    if hb is None:
        sup = _read_json(SUPERVISOR_STATE_PATH, default=None)
        if isinstance(sup, dict):
            hb = sup
            source = SUPERVISOR_STATE_PATH

    # derive age_ms if we can
    age_ms = None
    ts_s = None
    if isinstance(hb, dict):
        v = hb.get("timestamp")
        if isinstance(v, (int, float)):
            ts_s = float(v)

    if ts_s is not None:
        age_ms = int((now_s - ts_s) * 1000)

    return {
        "ok": hb is not None,
        "namespace": ns,
        "data_root": str(DATA_ROOT),
        "source_file": str(source) if source else None,
        "age_ms": age_ms,
        "now_s": now_s,
        "heartbeat": hb,
    }


# -----------------------------------------------------------------------------
# ADR demo actions
# -----------------------------------------------------------------------------
def adr_inject(stability: float = 0.45, drift_entropy: float = 0.92, source: str = "manual_inject") -> Dict[str, Any]:
    """
    Stressor for ADR: append a low-stability/high-entropy event into resonance_stream.jsonl.
    """
    RESONANCE_STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    evt = {
        "timestamp": time.time(),
        "stability": float(stability),
        "drift_entropy": float(drift_entropy),
        "source": source,
    }
    with open(RESONANCE_STREAM_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    return {"ok": True, "action": "adr_inject", "event": evt, **adr_state()}


def adr_run_resonance_feedback() -> Dict[str, Any]:
    """
    Execute PAL resonance-feedback once (writes drift_repair.log and pal_state.json).
    """
    import subprocess

    cmd = [sys.executable, "backend/modules/aion_perception/pal_core.py", "--mode=resonance-feedback"]
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", ".") or "."
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=45)
        out = (r.stdout or "").splitlines()[-25:]
        err = (r.stderr or "").splitlines()[-25:]
        return {
            "ok": r.returncode == 0,
            "action": "adr_run",
            "returncode": r.returncode,
            "stdout_tail": out,
            "stderr_tail": err,
            **adr_state(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "action": "adr_run", "error": "timeout", **adr_state()}


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="AION Demo Bridge", version="0.2.1")

# Keep CORS permissive for local dev demos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _maybe_autostart_heartbeat() -> None:
    """
    Optional: start resonance_heartbeat in the background if nothing is fresh.
    Off by default.
    """
    if not _truthy("AION_DEMO_AUTOSTART_HEARTBEAT", False):
        return

    # If the preferred namespace file exists and is fresh (< 2s), do nothing.
    preferred = HEARTBEAT_DIR / f"{DEFAULT_HEARTBEAT_NS}_heartbeat_live.json"
    try:
        if preferred.exists():
            age = time.time() - preferred.stat().st_mtime
            if age < 2.0:
                return
    except Exception:
        pass

    # Best-effort spawn (silent by default)
    try:
        import subprocess

        cmd = [
            sys.executable,
            "backend/modules/aion_resonance/resonance_heartbeat.py",
            "--namespace",
            DEFAULT_HEARTBEAT_NS,
        ]
        env = os.environ.copy()
        env.setdefault("AION_SILENT_MODE", "1")
        env.setdefault("PYTHONPATH", str(_REPO_ROOT))
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        # Never fail app startup because of autostart attempts
        return


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "aion-demo-bridge",
        "ts": time.time(),
        "data_root": str(DATA_ROOT),
        "default_heartbeat_namespace": DEFAULT_HEARTBEAT_NS,
    }

# --- Reflex (Demo 4) ---
@app.get("/api/reflex")
def api_reflex() -> Dict[str, Any]:
    st = reflex_mod.get_state(REFLEX_STATE_PATH)
    return {
        "ok": True,
        "data_root": str(DATA_ROOT),
        "source_file": str(REFLEX_STATE_PATH),
        "age_ms": st.get("age_ms"),
        "now_s": st.get("now_s"),
        "state": st,
    }

@app.post("/api/demo/reflex/reset")
def api_reflex_reset() -> Dict[str, Any]:
    st = reflex_mod.reset(REFLEX_STATE_PATH)
    return {"ok": True, "state": st}

@app.post("/api/demo/reflex/step")
async def api_reflex_step() -> Dict[str, Any]:
    st = await reflex_mod.step_once(REFLEX_STATE_PATH)
    return {"ok": True, "state": st}

@app.post("/api/demo/reflex/run")
async def api_reflex_run(steps: int = 60, interval_s: float = 0.25) -> Dict[str, Any]:
    st = await reflex_mod.start_run(REFLEX_STATE_PATH, steps=steps, interval_s=interval_s)
    return {"ok": True, "state": st}

# --- Φ endpoints ---
@app.get("/api/phi")
def api_phi() -> Dict[str, Any]:
    return phi_state()


@app.post("/api/demo/phi/reset")
def api_phi_reset() -> Dict[str, Any]:
    return phi_reset()


@app.post("/api/demo/phi/inject_entropy")
def api_phi_inject_entropy() -> Dict[str, Any]:
    return phi_inject_entropy(coherence=0.10, entropy=0.90)


@app.post("/api/demo/phi/recover")
def api_phi_recover() -> Dict[str, Any]:
    return phi_recover()


# --- ADR endpoints ---
@app.get("/api/adr")
def api_adr() -> Dict[str, Any]:
    return adr_state()


@app.post("/api/demo/adr/inject")
def api_adr_inject() -> Dict[str, Any]:
    return adr_inject(stability=0.45, drift_entropy=0.92, source="demo_bridge")


@app.post("/api/demo/adr/run")
def api_adr_run() -> Dict[str, Any]:
    return adr_run_resonance_feedback()


# --- Heartbeat endpoint (Demo 3) ---
@app.get("/api/heartbeat")
def api_heartbeat(
    namespace: Optional[str] = Query(default=None, description="Prefer <namespace>_heartbeat_live.json"),
) -> Dict[str, Any]:
    return heartbeat_state(namespace=namespace)


# --- Compat: old one-button endpoint (keeps older frontend calls working) ---
@app.post("/api/demo/inject_entropy")
def api_demo_inject_entropy() -> Dict[str, Any]:
    """
    Old "one button" demo:
      1) inject entropy into Φ metabolism (writes memory + reinforces)
      2) inject low-stability event into resonance stream
      3) run PAL resonance-feedback once (ADR can fire)
    """
    phi = phi_inject_entropy(coherence=0.10, entropy=0.90)
    adr = adr_inject(stability=0.45, drift_entropy=0.92, source="demo_bridge_inject_entropy")
    run = adr_run_resonance_feedback()
    return {"ok": True, "phi": phi, "adr": adr, "run": run, "ts": time.time()}


# --- Websocket streaming ---
# --- Websocket streaming ---
@app.websocket("/ws/aion-demo")
async def ws_aion_demo(ws: WebSocket) -> None:
    await ws.accept()
    interval_s = float(os.getenv("AION_DEMO_WS_INTERVAL_S", "0.5"))
    hb_ns = os.getenv("AION_DEMO_HEARTBEAT_NAMESPACE", DEFAULT_HEARTBEAT_NS)
    try:
        while True:
            payload = {
                "phi": phi_state(),
                "adr": adr_state(),
                "heartbeat": heartbeat_state(namespace=hb_ns),

                # ✅ Demo 4: Reflex (Cognitive Grid)
                "reflex": {
                    "ok": True,
                    "data_root": str(DATA_ROOT),
                    "source_file": str(REFLEX_STATE_PATH),
                    "state": reflex_mod.get_state(REFLEX_STATE_PATH),
                },

                "ts": time.time(),
            }
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
            await asyncio.sleep(interval_s)
    except WebSocketDisconnect:
        return
    except Exception:
        return


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("AION_DEMO_HOST", "127.0.0.1")
    port = int(os.getenv("AION_DEMO_PORT", "8007"))
    uvicorn.run("backend.modules.aion_demo.demo_bridge:app", host=host, port=port, reload=False)