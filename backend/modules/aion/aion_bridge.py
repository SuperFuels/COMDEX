# backend/modules/aion/aion_bridge.py
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Optional memory/telemetry hooks — all best-effort
try:
    from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
    RMC = ResonantMemoryCache()
except Exception:
    RMC = None

try:
    # GHX frontend bus so ContainerView “GHX feed” shows the event
    from backend.events.ghx_bus import broadcast
except Exception:
    async def broadcast(_cid: str, _msg: Dict[str, Any]):
        return  # graceful no-op

log = logging.getLogger(__name__)

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _derive_container_id(pkt: Dict[str, Any], fallback: str = "") -> str:
    # prefer explicit recipient; else hdr.route like "ucs://<id>"
    cid = (pkt.get("recipient")
           or (pkt.get("hdr") or {}).get("route", "").replace("ucs://", "")
           or fallback)
    return str(cid)

def _extract_wave_text(pkt: Dict[str, Any]) -> Optional[str]:
    # GIP “wave” op from PromptBar (/wave ...)
    body = pkt.get("body") or {}
    if body.get("op") == "wave":
        pld = body.get("payload") or {}
        val = pld.get("text")
        if isinstance(val, str):
            return val
    # Fallback: stringify payload
    payload = pkt.get("payload")
    if isinstance(payload, dict) and "text" in payload and isinstance(payload["text"], str):
        return payload["text"]
    return None

async def process_symbolic_input(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest a GIP packet into AION:
      • emit GHX event for UI,
      • persist a JSONL audit,
      • optionally touch ResonantMemoryCache (if available).
    Returns a small status dict.
    """
    cid = _derive_container_id(packet)
    text = _extract_wave_text(packet)

    # 1) Emit to GHX feed (so UI shows “aion_ingest”)
    try:
        await broadcast(cid, {
            "type": "aion_ingest",
            "container_id": cid,
            "payload": {"text": text} if text is not None else (packet.get("payload") or {}),
            "ts": _utcnow_iso(),
        })
    except Exception as e:
        log.warning(f"[AION] GHX broadcast failed: {e}")

    # 2) Append audit line (data/telemetry/aion_ingest.jsonl)
    try:
        import os
        os.makedirs("data/telemetry", exist_ok=True)
        with open("data/telemetry/aion_ingest.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": _utcnow_iso(),
                "container_id": cid,
                "packet_id": packet.get("id"),
                "op": (packet.get("body") or {}).get("op"),
                "text": text,
            }) + "\n")
    except Exception as e:
        log.warning(f"[AION] audit write failed: {e}")

    # 3) Lightweight memory touch (optional, safe)
    try:
        if RMC and text:
            # cache semantics differ by build; fall back to simple set
            if hasattr(RMC, "remember"):
                RMC.remember(text, {"definition": text, "resonance": 0.0})
            elif hasattr(RMC, "cache"):
                RMC.cache[text] = RMC.cache.get(text, {"definition": text, "resonance": 0.0})
    except Exception as e:
        log.debug(f"[AION] RMC touch failed: {e}")

    return {"status": "ok", "ingested": True, "container_id": cid, "text": text}