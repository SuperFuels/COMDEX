# File: backend/routers/gip_api.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

# GHX feed
from backend.events.ghx_bus import broadcast

# GIP packet utils
from backend.modules.gip.gip_packet_schema import validate_gip_packet
from backend.modules.gip.gip_packet import create_gip_packet, parse_gip_packet

# Fan-out to Codex and AION (uses working forward_packet_to_codex)
from backend.modules.gip.gip_broadcast import broadcast_to_codex_and_aion

# --- QKD (optional, auto-detected) ---
try:
    from backend.modules.glyphwave.qkd.qkd_policy_enforcer import enforce_qkd_policy  # type: ignore
    from backend.modules.glyphwave.qkd.qkd_manager import get_qkd_manager  # type: ignore
    HAS_QKD = True
except Exception:
    enforce_qkd_policy = None  # type: ignore
    get_qkd_manager = None  # type: ignore
    HAS_QKD = False

router = APIRouter(tags=["GIP"])


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_cid_from_frame(body: Dict[str, Any]) -> str:
    # Try hdr.route: "ucs://<id>"
    route = (body.get("hdr") or {}).get("route")
    if isinstance(route, str) and route.startswith("ucs://"):
        return route[len("ucs://") :]

    # Try explicit recipient
    if isinstance(body.get("recipient"), str):
        return body["recipient"]

    # Try payload.meta.recipient (or body.meta)
    payload = body.get("payload") or body.get("body") or {}
    meta = (payload.get("meta") if isinstance(payload, dict) else None) or {}
    rec = meta.get("recipient")
    if isinstance(rec, str):
        return rec

    return ""


async def _handle_gip_send(container_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts:
      - {"command": "..."}                    -> executes symbolic terminal command (if present)
      - "frame" dict: {hdr:{...}, body:{...}} -> wraps in GIPPacket (payload=frame)
      - already-normalized GIPPacket dict     -> passes through after normalization/validation
      - minimal payload dict                  -> wraps into GIPPacket(payload=...)
    Emits GHX events and fans out to Codex/AION. Enforces QKD if requested.
    """
    cid = (container_id or "").strip()

    # 1) Command-mode (keep parity with WS path)
    if "command" in body:
        # import lazily to avoid hard dep in builds that omit terminal
        try:
            from backend.modules.glyphnet.glyphnet_terminal import run_symbolic_command  # type: ignore
        except Exception:
            raise HTTPException(501, "Symbolic terminal unavailable on this build")
        try:
            result = run_symbolic_command(body["command"])
            await broadcast(cid or "ucs_hub", {
                "event": "gip_command",
                "container_id": cid or "ucs_hub",
                "payload": {
                    "command": body["command"],
                    "result": result,
                },
                "ts": _utcnow_iso(),
            })
            return {"ok": True, "kind": "command", "result": result}
        except Exception as e:
            raise HTTPException(400, f"Command failed: {e}")

    # 2) Normalize to GIPPacket
    try:
        pkt: Dict[str, Any]

        # Case: client already sent a GIPPacket dictionary
        if all(k in body for k in ("sender", "recipient", "payload")):
            body.setdefault("type", "gip")
            body.setdefault("encoding", "glyph")
            body.setdefault("compression", "symbolic")
            pkt = parse_gip_packet(body)

        # Case: GIP "frame" from PromptBar (/wave …) -> wrap into payload
        elif "hdr" in body and "body" in body:
            recipient = cid or _derive_cid_from_frame(body) or "ucs_hub"
            pkt = create_gip_packet(
                sender=body.get("sender", "browser"),
                recipient=recipient,
                payload={"frame": body},  # keep header+body intact
            )
            pkt.setdefault("type", "gip")

        # Case: minimal dict -> treat as payload
        else:
            recipient = cid or body.get("recipient") or "ucs_hub"
            payload = body if "payload" not in body else body["payload"]
            pkt = create_gip_packet(
                sender=body.get("sender", "browser"),
                recipient=recipient,
                payload=payload,
            )
            pkt.setdefault("type", "gip")

        validate_gip_packet(pkt)  # permissive (only requires top-level type)
    except Exception as e:
        raise HTTPException(400, f"Invalid GIP payload: {e}")

    # 3) Optional QKD policy
    meta: Dict[str, Any] = {}
    qkd_required: Optional[str | bool] = False
    try:
        # look inside payload first (frame/body/meta), then top-level meta
        pl = pkt.get("payload") or {}
        if isinstance(pl, dict):
            # payload may be {"frame": {hdr, body}} or a raw op dict
            fr = pl.get("frame") if isinstance(pl.get("frame"), dict) else pl
            inner = fr.get("body") if isinstance(fr, dict) and isinstance(fr.get("body"), dict) else fr
            meta = (inner.get("meta") if isinstance(inner, dict) else None) or fr.get("meta") or {}
        if not meta:
            meta = pkt.get("meta", {}) or {}

        qkd_required = meta.get("qkd_required", False)
        session_id = meta.get("qkd_session_id") or meta.get("session_id") or pkt.get("recipient") or cid

        if qkd_required and HAS_QKD and enforce_qkd_policy and get_qkd_manager:
            qmgr = get_qkd_manager()
            gkey = qmgr.get_active_gkey(session_id) if hasattr(qmgr, "get_active_gkey") else qmgr.get(session_id)
            ok = enforce_qkd_policy(pkt, gkey)
            if not ok:
                await broadcast(cid or "ucs_hub", {
                    "event": "qkd_denied",
                    "container_id": cid or "ucs_hub",
                    "payload": {
                        "packet_id": pkt.get("id"),
                    },
                    "ts": _utcnow_iso(),
                })
                raise HTTPException(403, "QKD policy enforcement failed")
    except HTTPException:
        raise
    except Exception as qerr:
        # Only hard-fail if strict
        mode = "strict" if qkd_required == "strict" else ""
        if qkd_required in (True, "strict") or mode == "strict":
            raise HTTPException(403, f"QKD enforcement error: {qerr}")
        await broadcast(cid or "ucs_hub", {
            "event": "qkd_warning",
            "container_id": cid or "ucs_hub",
            "payload": {
                "packet_id": pkt.get("id"),
                "message": str(qerr),
            },
            "ts": _utcnow_iso(),
        })

    # 4) Fan-out (fire-and-forget) to Codex & AION
    try:
        asyncio.create_task(broadcast_to_codex_and_aion(pkt))
    except Exception:
        pass  # best-effort

    # 5) GHX feed for UI
    try:
        await broadcast(cid or "ucs_hub", {
            "event": "gip_frame",
            "container_id": cid or "ucs_hub",
            "payload": pkt,
            "ts": _utcnow_iso(),
        })
    except Exception as e:
        raise HTTPException(500, f"GHX broadcast failed: {e}")

    return {"ok": True, "packet_id": pkt.get("id"), "recipient": pkt.get("recipient")}


@router.post("/api/gip/send/{container_id}")
async def gip_send(container_id: str, req: Request):
    body = await req.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON object required")
    return await _handle_gip_send(container_id.strip(), body)


@router.post("/api/gip/send")
async def gip_send_no_id(req: Request):
    body = await req.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON object required")
    cid = _derive_cid_from_frame(body) or body.get("recipient") or "ucs_hub"
    return await _handle_gip_send(cid, body)