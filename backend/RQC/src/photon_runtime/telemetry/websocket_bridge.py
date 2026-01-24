from __future__ import annotations
"""
Tessaris RQC - WebSocket Telemetry Bridge
-----------------------------------------
Real-time bridge that streams ψ-κ-T-Φ resonance metrics to connected frontends.

IMPORTANT: In your stack there are (at least) two ledger shapes:
  A) MorphicLedger records (often nested under {"tensor": {...}, "phi": ...})
  B) RQC/GHX telemetry snapshots (flat), written to:
       data/ledger/rqc_live_telemetry.jsonl
     with keys like:
       Φ_mean, ψ_mean, resonance_index, coherence_energy, κ, T, event

This bridge supports BOTH. It tails the active ledger JSONL file and broadcasts each
new record as a JSON message over WebSocket.

Ledger file resolution order:
  1) RQC_LEDGER_FILE (explicit path)
  2) MORPHIC_LEDGER_FILE (explicit path)
  3) morphic_ledger.ledger_path (if available)
  4) data/ledger/rqc_live_telemetry.jsonl (default; what your backend expects)

Endpoints:
  ws://localhost:<RQC_WS_PORT>/<RQC_WS_PATH>
"""

import asyncio
import json
import os
import logging
from datetime import datetime, UTC
from typing import Dict, Any, Set, Optional

import websockets

logger = logging.getLogger("rqc.websocket")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="[%(asctime)s] %(message)s")

WS_PORT = int(os.getenv("RQC_WS_PORT", "7070"))
WS_HOST = os.getenv("RQC_WS_HOST", "0.0.0.0")
WS_PATH = os.getenv("RQC_WS_PATH", "/resonance")

AWARENESS_PULSE_THRESHOLD = float(os.getenv("AWARENESS_PULSE_THRESHOLD", "0.999"))
TAIL_POLL_S = float(os.getenv("RQC_TAIL_POLL_S", "0.25"))

clients: Set[websockets.WebSocketServerProtocol] = set()


def strip_slash(p: str) -> str:
    return (p or "").strip()


def resolve_ledger_path() -> str:
    # explicit override wins
    p = strip_slash(os.getenv("RQC_LEDGER_FILE", ""))
    if p:
        return p
    p = strip_slash(os.getenv("MORPHIC_LEDGER_FILE", ""))
    if p:
        return p

    # try morphic_ledger if present
    try:
        from backend.modules.holograms.morphic_ledger import morphic_ledger  # type: ignore
        lp = getattr(morphic_ledger, "ledger_path", None)
        if lp:
            return str(lp)
    except Exception:
        pass

    # default expected by your backend stack
    return "data/ledger/rqc_live_telemetry.jsonl"


# ──────────────────────────────────────────────
# WS core
# ──────────────────────────────────────────────

async def broadcast(message: Dict[str, Any]) -> None:
    if not clients:
        return

    data = json.dumps(message, ensure_ascii=False)

    dead: Set[websockets.WebSocketServerProtocol] = set()
    send_tasks = []
    live_clients = list(clients)

    for c in live_clients:
        if getattr(c, "open", False):
            send_tasks.append(c.send(data))
        else:
            dead.add(c)

    if send_tasks:
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        # map results back to the same ordering
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                try:
                    dead.add(live_clients[i])
                except Exception:
                    pass

    for c in dead:
        clients.discard(c)


async def handle_client(websocket, path) -> None:
    if path != WS_PATH:
        try:
            await websocket.close(code=1008, reason="Invalid path")
        finally:
            return

    clients.add(websocket)
    logger.info(f"[+] Client connected ({len(clients)} total)")

    try:
        await websocket.send(json.dumps(
            {
                "type": "hello",
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "Connected to Tessaris RQC WebSocket Bridge",
                "ledger_path": resolve_ledger_path(),
                "pulse_threshold": AWARENESS_PULSE_THRESHOLD,
            },
            ensure_ascii=False,
        ))

        async for _ in websocket:
            # push-only
            pass
    except Exception as e:
        logger.warning(f"Client error: {e}")
    finally:
        clients.discard(websocket)
        logger.info(f"[-] Client disconnected ({len(clients)} total)")


# ──────────────────────────────────────────────
# Normalization (supports BOTH schemas)
# ──────────────────────────────────────────────

def normalize_entry(entry: Dict[str, Any], source_pair: str) -> Optional[Dict[str, Any]]:
    """
    Returns a broadcastable telemetry packet or None to ignore the line.
    Supports:
      A) MorphicLedger:
         {"id":..., "tensor":{"psi":..,"kappa":..,"T":..,"coherence":..}, "phi":.., "meta":{...}}
      B) RQC/GHX telemetry:
         {"timestamp":.., "Φ_mean":.., "ψ_mean":.., "resonance_index":.., "coherence_energy":.., "κ":.., "T":.., "event":..}
    """

    # ignore probe / non-record lines
    if entry.get("type") == "_probe":
        return None

    tensor = entry.get("tensor") or {}

    # --- Φ (awareness)
    Φ = (
        entry.get("Φ")
        or entry.get("\u03a6")  # "Φ"
        or entry.get("phi")
        or entry.get("Φ_mean")
        or entry.get("Phi")
        or tensor.get("phi")
        or 0.0
    )

    # --- ψ
    ψ = (
        entry.get("ψ")
        or entry.get("psi")
        or entry.get("ψ_mean")
        or tensor.get("psi")
        or None
    )

    # --- κ
    κ = (
        entry.get("κ")
        or entry.get("kappa")
        or entry.get("κ_mean")
        or tensor.get("kappa")
        or None
    )

    # --- T
    T = (
        entry.get("T")
        or entry.get("T_mean")
        or tensor.get("T")
        or None
    )

    # --- coherence-like scalar (pick best available)
    coherence = (
        entry.get("coherence")
        or entry.get("C")
        or entry.get("Φ_coherence")
        or entry.get("coherence_energy")
        or entry.get("resonance_index")
        or tensor.get("coherence")
        or 0.0
    )

    # some lines might not be telemetry at all
    looks_like_telemetry = any([
        "tensor" in entry,
        "Φ_mean" in entry,
        "coherence_energy" in entry,
        "resonance_index" in entry,
        "ψ_mean" in entry,
        "κ" in entry,
        "kappa" in entry,
        "Φ" in entry,
        "phi" in entry,
    ])
    if not looks_like_telemetry:
        return None

    meta = entry.get("meta") or entry.get("metadata") or {}
    operator = None
    if isinstance(meta, dict):
        operator = meta.get("operator") or meta.get("op") or meta.get("op_name")

    ev = entry.get("event") or entry.get("type") or "telemetry"

    return {
        "type": "telemetry",
        "timestamp": datetime.now(UTC).isoformat(),
        "id": entry.get("id"),
        "ψ": ψ,
        "κ": κ,
        "T": T,
        "Φ": float(Φ) if Φ is not None else 0.0,
        "coherence": float(coherence) if coherence is not None else 0.0,
        "event": ev,
        "operator": operator,
        "source": source_pair,
    }


# ──────────────────────────────────────────────
# Tailer (handles truncation/rotation)
# ──────────────────────────────────────────────

async def tail_jsonl(path: str, poll_s: float = TAIL_POLL_S) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not os.path.exists(path):
        open(path, "a", encoding="utf-8").close()

    logger.info(f"📡 Watching ledger -> {path}")

    # We track inode+size so if file is rotated/truncated we re-open + seek end.
    last_inode: Optional[int] = None
    last_pos: int = 0

    while True:
        try:
            st = os.stat(path)
            inode = getattr(st, "st_ino", None)
            size = st.st_size

            rotated = (last_inode is not None and inode is not None and inode != last_inode)
            truncated = (size < last_pos)

            if rotated or truncated or last_inode is None:
                last_inode = inode
                last_pos = 0

            with open(path, "r", encoding="utf-8") as f:
                # seek to last_pos, but if first open, seek to end (stream only new)
                if last_pos == 0 and (rotated or truncated or last_inode is None):
                    f.seek(0, os.SEEK_END)
                    last_pos = f.tell()
                else:
                    f.seek(last_pos, os.SEEK_SET)

                while True:
                    line = f.readline()
                    if not line:
                        last_pos = f.tell()
                        break

                    s = line.strip()
                    if not s:
                        continue

                    try:
                        entry = json.loads(s)
                    except Exception:
                        continue

                    source_pair = f"{os.path.basename(path)}"
                    msg = normalize_entry(entry, source_pair)
                    if not msg:
                        continue

                    await broadcast(msg)

                    Φ = msg.get("Φ", 0.0) or 0.0
                    C = msg.get("coherence", 0.0) or 0.0

                    if float(Φ) >= AWARENESS_PULSE_THRESHOLD:
                        pulse = {
                            "type": "awareness_pulse",
                            "timestamp": datetime.now(UTC).isoformat(),
                            "message": "🧠 Awareness resonance closure detected",
                            "Φ": float(Φ),
                            "coherence": float(C),
                            "id": msg.get("id"),
                            "source": source_pair,
                        }
                        await broadcast(pulse)
                        logger.info(f"[🧠] pulse Φ={float(Φ):.3f} C={float(C):.3f}")
                    else:
                        logger.info(f"[->] Φ={float(Φ):.3f} C={float(C):.3f}")

        except FileNotFoundError:
            # file might appear later
            pass
        except Exception as e:
            logger.warning(f"[⚠️] tail error: {e}")

        await asyncio.sleep(poll_s)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

async def main() -> None:
    ledger_path = resolve_ledger_path()

    logger.info("🔭 Tessaris RQC - Starting WebSocket Bridge...")
    server = await websockets.serve(
        handle_client,
        WS_HOST,
        WS_PORT,
        ping_interval=20,
        ping_timeout=60,
    )
    logger.info(f"✅ Listening on ws://localhost:{WS_PORT}{WS_PATH}")
    await tail_jsonl(ledger_path)
    await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 WebSocket bridge stopped.")