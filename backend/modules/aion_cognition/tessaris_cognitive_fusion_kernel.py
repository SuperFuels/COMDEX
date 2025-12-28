#!/usr/bin/env python3
"""
Tessaris Phase 29 - Cognitive Fusion Kernel (TCFK)
────────────────────────────────────────────────────
Unifies resonant analytics (RAL) + symbolic cognition (SIN, optional) + (optional) AQCI
into a single coherent fusion state, broadcast over WebSocket.

Outputs:
- WebSocket: ws://0.0.0.0:8005/ws/fusion
- Log: data/learning/fusion_state.jsonl
"""

import asyncio
import json
import os
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets
from websockets.exceptions import ConnectionClosed

# ✅ SCI overlay for symbolic cognition trace (safe fallback)
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k):
        pass


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
RAL_STREAM = "ws://localhost:8002/ws/analytics"
SIN_STREAM = (os.getenv("AION_SIN_STREAM", "") or "").strip() or None  # optional
AQCI_FEED = "ws://localhost:8004/ws/control"  # optional feedback

FUSION_WS_HOST = "0.0.0.0"
FUSION_WS_PORT = 8005
FUSION_WS_PATH = "/ws/fusion"

FUSION_LOG = Path("data/learning/fusion_state.jsonl")
FUSION_LOG.parent.mkdir(parents=True, exist_ok=True)

# If raw feeds aren't CHANGING for this long, synthesize motion for HUD-facing ψ̃ / κ̃
CURL_STALE_MS = 1800
PSI_STALE_MS = 1800

# raw-change threshold (to decide if feed is "changing")
EPS_CURL_RAW = 1e-4
EPS_PSI_RAW = 1e-4

# published-change threshold (for debugging / metrics; not used for stale detection)
EPS_CURL = 1e-4
EPS_PSI = 1e-4


# ─────────────────────────────────────────────
# State
# ─────────────────────────────────────────────
CLIENTS = set()
CLIENTS_LOCK = asyncio.Lock()
STATE_LOCK = asyncio.Lock()

fusion_state = {
    # core (published / HUD-facing)
    "stability": 1.0,          # σ
    "entropy": 0.0,
    "cognition_signal": 0.0,   # ψ̃  (published value the HUD uses)

    # fusion outputs
    "fusion_coherence": 1.0,
    "coherence": 1.0,
    "delta_coherence": 0.0,

    # extras for HUDs (published / HUD-facing)
    "curl_rms": 0.0,           # κ̃  (published value the HUD uses)
    "curv": 0.0,
    "coupling_score": 1.0,     # γ̃
    "max_norm": 0.0,
    "fusion_score": 1.0,

    # raw inputs (do NOT render directly; listeners write here)
    "_ral_curl_rms": None,         # raw curl from RAL
    "_sin_cognition_signal": None, # raw psi from SIN

    # bookkeeping
    "timestamp": None,
    "updatedAt_ms": None,
    "src": {"ral": False, "sin": False},
}

# last time socket streams delivered any packet
last_seen = {"ral_ms": 0, "sin_ms": 0}

# Track "last time RAW value actually changed" (used for stale detection)
last_raw_change = {
    "curl_v": None,
    "curl_ms": 0,
    "psi_v": None,
    "psi_ms": 0,
}

# Track "last time PUBLISHED value actually changed" (debug only)
last_pub_change = {
    "curl_v": None,
    "curl_ms": 0,
    "psi_v": None,
    "psi_ms": 0,
}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def now_ms() -> int:
    return int(time.time() * 1000)

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def pick_num(*vals, default=0.0) -> float:
    for v in vals:
        try:
            n = float(v)
            if math.isfinite(n):
                return n
        except Exception:
            continue
    return float(default)

def pick_opt_num(*vals):
    """
    Like pick_num, but returns None if no finite number found.
    """
    for v in vals:
        try:
            n = float(v)
            if math.isfinite(n):
                return float(n)
        except Exception:
            continue
    return None

def compute_fusion_coherence(stability: float, entropy: float, cognition_signal: float) -> float:
    try:
        a, b, g = 0.45, 0.45, 0.10
        s_term = a * clamp(stability, 0.0, 1.0)
        e_term = b * (1.0 - clamp(entropy, 0.0, 1.0))
        c_term = g * math.tanh(abs(cognition_signal))
        return clamp(s_term + e_term + c_term, 0.0, 1.0)
    except Exception:
        return 0.0

def hud_aliases(*, stability: float, coupling_score: float, cognition_signal: float, curl_rms: float) -> dict:
    return {
        # ASCII aliases
        "sigma": stability,
        "gamma_tilde": coupling_score,
        "psi_tilde": cognition_signal,
        "kappa_tilde": curl_rms,

        # Unicode aliases
        "σ": stability,
        "γ̃": coupling_score,
        "ψ̃": cognition_signal,
        "κ̃": curl_rms,
    }

def _mark_change(store: dict, key: str, value: float, eps: float) -> None:
    ms = now_ms()
    v_key = f"{key}_v"
    ms_key = f"{key}_ms"
    prev = store.get(v_key, None)
    if prev is None or abs(float(value) - float(prev)) > eps:
        store[v_key] = float(value)
        store[ms_key] = ms

def mark_raw_change(key: str, value: float, eps: float) -> None:
    _mark_change(last_raw_change, key, value, eps)

def mark_change(key: str, value: float, eps: float) -> None:
    # published change (debug only)
    _mark_change(last_pub_change, key, value, eps)

def is_stale(key: str, stale_ms: int) -> bool:
    """
    IMPORTANT: stale detection is based on RAW feed change, not published motion.
    """
    ms_key = f"{key}_ms"
    last = int(last_raw_change.get(ms_key, 0) or 0)
    return (now_ms() - last) > stale_ms

async def safe_send(ws, payload: str) -> bool:
    try:
        await ws.send(payload)
        return True
    except ConnectionClosed:
        return False
    except Exception:
        return False

async def broadcast(payload: dict) -> None:
    msg = json.dumps(payload)
    async with CLIENTS_LOCK:
        if not CLIENTS:
            return
        dead = []
        for c in list(CLIENTS):
            ok = await safe_send(c, msg)
            if not ok:
                dead.append(c)
        for c in dead:
            try:
                CLIENTS.remove(c)
            except Exception:
                pass

def log_state(state: dict) -> None:
    try:
        with open(FUSION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(state) + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────
# WebSocket server
# ─────────────────────────────────────────────
async def fusion_ws_handler(websocket):
    path = getattr(websocket, "path", "") or ""
    if path not in (FUSION_WS_PATH, "/", ""):
        try:
            await websocket.close(code=1008, reason="invalid path")
        except Exception:
            pass
        return

    async with CLIENTS_LOCK:
        CLIENTS.add(websocket)

    # hello includes aliases (READ ONLY; synth happens in fusion_loop)
    async with STATE_LOCK:
        stability = float(fusion_state.get("stability", 1.0))
        entropy = float(fusion_state.get("entropy", 0.0))
        cognition_signal = float(fusion_state.get("cognition_signal", 0.0))  # ψ̃
        curl_rms = float(fusion_state.get("curl_rms", 0.0))                  # κ̃
        coupling_score = float(fusion_state.get("coupling_score", 1.0))      # γ̃

        hello = {
            "type": "hello",
            "status": "connected",
            "timestamp": utc_iso(),
            "updatedAt_ms": now_ms(),

            "stability": stability,
            "entropy": entropy,

            "cognition_signal": cognition_signal,
            "curl_rms": curl_rms,
            "coupling_score": coupling_score,

            "fusion_coherence": fusion_state.get("fusion_coherence", 1.0),
            "coherence": fusion_state.get("coherence", fusion_state.get("fusion_coherence", 1.0)),

            "curv": fusion_state.get("curv", 0.0),
            "max_norm": fusion_state.get("max_norm", 0.0),
            "src": dict(fusion_state.get("src", {})),

            # raw (debug)
            "_sin_cognition_signal": fusion_state.get("_sin_cognition_signal"),
            "_ral_curl_rms": fusion_state.get("_ral_curl_rms"),

            **hud_aliases(
                stability=stability,
                coupling_score=coupling_score,
                cognition_signal=cognition_signal,
                curl_rms=curl_rms,
            ),
        }

    await safe_send(websocket, json.dumps(hello))

    try:
        async for message in websocket:
            if (message or "").strip().lower() == "ping":
                await safe_send(websocket, json.dumps({"type": "pong", "ts": utc_iso()}))
    finally:
        async with CLIENTS_LOCK:
            try:
                CLIENTS.remove(websocket)
            except Exception:
                pass


# ─────────────────────────────────────────────
# Upstream listeners (WRITE RAW ONLY)
# ─────────────────────────────────────────────
async def listen_ral():
    backoff = 1.0
    while True:
        try:
            async with websockets.connect(RAL_STREAM, ping_interval=20, ping_timeout=20) as ws:
                backoff = 1.0
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue

                    stability = pick_num(
                        data.get("stability"), data.get("sigma"), data.get("coherence"),
                        default=fusion_state.get("stability", 1.0)
                    )
                    entropy = pick_num(
                        data.get("drift_entropy"), data.get("entropy"),
                        default=fusion_state.get("entropy", 0.0)
                    )

                    # raw curl: only from feed (do NOT overwrite HUD-facing curl_rms here)
                    curl_raw = pick_opt_num(data.get("curl_rms"), data.get("curl"))

                    curv = pick_num(data.get("curv"), data.get("curvature"),
                                    default=fusion_state.get("curv", 0.0))
                    max_norm = pick_num(data.get("max_norm"),
                                        default=fusion_state.get("max_norm", 0.0))

                    async with STATE_LOCK:
                        fusion_state["stability"] = clamp(stability, 0.0, 1.0)
                        fusion_state["entropy"] = clamp(entropy, 0.0, 1.0)
                        fusion_state["curv"] = float(curv)
                        fusion_state["max_norm"] = max(0.0, float(max_norm))
                        fusion_state["src"]["ral"] = True

                        if curl_raw is not None:
                            fusion_state["_ral_curl_rms"] = max(0.0, float(curl_raw))
                            mark_raw_change("curl", fusion_state["_ral_curl_rms"], EPS_CURL_RAW)

                    last_seen["ral_ms"] = now_ms()

        except Exception as e:
            async with STATE_LOCK:
                fusion_state["src"]["ral"] = False
            print(f"⚠️ RAL stream disconnected: {e} (retry in {backoff:.1f}s)")
            await asyncio.sleep(backoff)
            backoff = min(10.0, backoff * 1.6)

async def listen_sin():
    if not SIN_STREAM:
        async with STATE_LOCK:
            fusion_state["src"]["sin"] = False
        print("🧠 SIN disabled (AION_SIN_STREAM not set).")
        while True:
            await asyncio.sleep(3600)

    backoff = 1.5
    while True:
        try:
            async with websockets.connect(SIN_STREAM, ping_interval=20, ping_timeout=20) as ws:
                backoff = 1.5
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue

                    psi_raw = pick_opt_num(
                        data.get("inference_strength"),
                        data.get("cognition_signal"),
                        data.get("signal"),
                        data.get("ψ̃"),
                        data.get("psi_tilde"),
                    )

                    async with STATE_LOCK:
                        fusion_state["src"]["sin"] = True
                        if psi_raw is not None:
                            fusion_state["_sin_cognition_signal"] = float(psi_raw)
                            mark_raw_change("psi", fusion_state["_sin_cognition_signal"], EPS_PSI_RAW)

                    last_seen["sin_ms"] = now_ms()

        except Exception:
            async with STATE_LOCK:
                fusion_state["src"]["sin"] = False
            await asyncio.sleep(backoff)
            backoff = min(12.0, backoff * 1.6)


# ─────────────────────────────────────────────
# Synthetic motion for stability/entropy if feeds go dead (does NOT touch ψ̃/κ̃)
# ─────────────────────────────────────────────
async def synth_motion_loop():
    t0 = time.time()
    while True:
        await asyncio.sleep(0.25)
        ms = now_ms()
        ral_dead = (ms - last_seen["ral_ms"]) > 2500
        sin_dead = (ms - last_seen["sin_ms"]) > 2500

        if not ral_dead and not sin_dead:
            continue

        x = time.time() - t0
        wob1 = 0.5 + 0.5 * math.sin(x * 0.9)
        wob2 = 0.5 + 0.5 * math.sin(x * 0.42 + 1.2)
        noise = (random.random() - 0.5) * 0.02

        async with STATE_LOCK:
            if ral_dead:
                fusion_state["stability"] = clamp(0.88 + 0.07 * wob2 + noise, 0.0, 1.0)
                fusion_state["entropy"] = clamp(0.06 + 0.05 * (1 - wob1) + noise, 0.0, 1.0)
                fusion_state["curv"] = float(0.01 + 0.03 * wob2 + noise)


# ─────────────────────────────────────────────
# Fusion core loop (DECIDES HUD-facing ψ̃/κ̃)
# ─────────────────────────────────────────────
async def fusion_loop():
    prev = float(fusion_state.get("fusion_coherence", 1.0))

    while True:
        # snapshot inputs
        async with STATE_LOCK:
            stability = float(fusion_state.get("stability", 1.0))
            entropy = float(fusion_state.get("entropy", 0.0))

            psi_raw = fusion_state.get("_sin_cognition_signal")
            curl_raw = fusion_state.get("_ral_curl_rms")

            curv = float(fusion_state.get("curv", 0.0))
            max_norm = float(fusion_state.get("max_norm", 0.0))

        # decide ψ̃ (prefer SIN only if its RAW is actively changing)
        if psi_raw is not None and not is_stale("psi", PSI_STALE_MS):
            cognition_signal = float(psi_raw)
        else:
            t = time.time()
            cognition_signal = math.sin(t * 1.25) * 0.55 + (random.random() - 0.5) * 0.03

        # decide κ̃ (prefer RAL only if its RAW is actively changing)
        if curl_raw is not None and not is_stale("curl", CURL_STALE_MS):
            curl_rms = float(curl_raw)
        else:
            t = time.time()
            curl_rms = 0.02 + 0.05 * abs(math.sin(t * 1.1 + cognition_signal * 1.7))
            curl_rms = clamp(curl_rms, 0.0, 0.35)

        # fusion metrics
        coherence = compute_fusion_coherence(stability, entropy, cognition_signal)
        delta = coherence - prev
        prev = coherence

        coupling_score = clamp(0.55 * coherence + 0.45 * stability, 0.0, 1.0)
        fusion_score = coherence

        stamp = utc_iso()
        ms = now_ms()

        async with STATE_LOCK:
            # ✅ publish HUD-facing ψ̃/κ̃ (movement happens here)
            fusion_state["cognition_signal"] = float(cognition_signal)
            fusion_state["curl_rms"] = float(curl_rms)

            # ✅ (requested) track published change
            mark_change("psi", fusion_state["cognition_signal"], EPS_PSI)
            mark_change("curl", fusion_state["curl_rms"], EPS_CURL)

            fusion_state.update({
                "fusion_coherence": coherence,
                "coherence": coherence,
                "delta_coherence": delta,
                "coupling_score": coupling_score,
                "fusion_score": fusion_score,
                "timestamp": stamp,
                "updatedAt_ms": ms,

                # keep these visible in the packet
                "curv": curv,
                "max_norm": max_norm,

                **hud_aliases(
                    stability=stability,
                    coupling_score=coupling_score,
                    cognition_signal=fusion_state["cognition_signal"],
                    curl_rms=fusion_state["curl_rms"],
                ),
            })
            snap = dict(fusion_state)

        try:
            sci_emit(
                "fusion_update",
                f"Φ={coherence:.3f} Δ={delta:+.4f} S={stability:.3f} H={entropy:.3f} "
                f"ψ={cognition_signal:.3f} κ={curl_rms:.4f}"
            )
        except Exception:
            pass

        log_state(snap)

        # optional adaptive feedback (best-effort)
        if abs(delta) > 0.010 and AQCI_FEED:
            try:
                async with websockets.connect(AQCI_FEED, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(json.dumps({
                        "type": "coherence_adjustment",
                        "delta": delta,
                        "timestamp": stamp,
                    }))
            except Exception:
                pass

        await asyncio.sleep(0.75)


# ─────────────────────────────────────────────
# Broadcasters
# ─────────────────────────────────────────────
async def broadcast_fusion():
    while True:
        async with STATE_LOCK:
            ready = fusion_state.get("timestamp") is not None
            snap = dict(fusion_state)
        if ready:
            await broadcast(snap)
        await asyncio.sleep(0.35)

async def heartbeat_broadcast():
    while True:
        async with STATE_LOCK:
            stability = float(fusion_state.get("stability", 1.0))
            coupling_score = float(fusion_state.get("coupling_score", 1.0))
            cognition_signal = float(fusion_state.get("cognition_signal", 0.0))
            curl_rms = float(fusion_state.get("curl_rms", 0.0))

            hb = {
                "type": "heartbeat",
                "timestamp": utc_iso(),
                "updatedAt_ms": now_ms(),
                "fusion_coherence": fusion_state.get("fusion_coherence", 1.0),

                "stability": stability,
                "entropy": fusion_state.get("entropy", 0.0),
                "cognition_signal": cognition_signal,
                "coupling_score": coupling_score,
                "curl_rms": curl_rms,

                "curv": fusion_state.get("curv", 0.0),
                "max_norm": fusion_state.get("max_norm", 0.0),
                "src": dict(fusion_state.get("src", {})),

                **hud_aliases(
                    stability=stability,
                    coupling_score=coupling_score,
                    cognition_signal=cognition_signal,
                    curl_rms=curl_rms,
                ),
            }

        await broadcast(hb)
        await asyncio.sleep(5.0)


# ─────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────
async def main():
    print("🧠 Starting Tessaris Cognitive Fusion Kernel (TCFK)...")

    await websockets.serve(
        fusion_ws_handler,
        FUSION_WS_HOST,
        FUSION_WS_PORT,
        ping_interval=20,
        ping_timeout=20,
        max_queue=64,
    )
    print(f"🌐 Fusion WS running on ws://{FUSION_WS_HOST}:{FUSION_WS_PORT}{FUSION_WS_PATH}")

    async with STATE_LOCK:
        fusion_state["timestamp"] = utc_iso()
        fusion_state["updatedAt_ms"] = now_ms()

        # seed raw-change timers so stale detection works immediately
        # (treat "no raw yet" as stale after interval; timers start now)
        last_raw_change["psi_ms"] = now_ms()
        last_raw_change["curl_ms"] = now_ms()

        # seed aliases on first packet
        stability = float(fusion_state.get("stability", 1.0))
        coupling_score = float(fusion_state.get("coupling_score", 1.0))
        cognition_signal = float(fusion_state.get("cognition_signal", 0.0))
        curl_rms = float(fusion_state.get("curl_rms", 0.0))
        fusion_state.update(hud_aliases(
            stability=stability,
            coupling_score=coupling_score,
            cognition_signal=cognition_signal,
            curl_rms=curl_rms,
        ))

    await asyncio.gather(
        listen_ral(),
        listen_sin(),
        synth_motion_loop(),
        fusion_loop(),
        broadcast_fusion(),
        heartbeat_broadcast(),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🧩 TCFK stopped.")