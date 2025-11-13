# backend/routes/voice.py
import os
import time
import hmac
import base64
import hashlib
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, Request, HTTPException, Response

# ──────────────────────────────────────────────────────────────
# ENV (set these in your server environment)
#   TWILIO_AUTH_TOKEN      -> for X-Twilio-Signature validation
#   PUBLIC_BASE_URL        -> your public https base (exactly what Twilio hits)
#   INTERNAL_BASE          -> where your app accepts /api/glyphnet/tx (default http://localhost:8080)
#   DEV_ALLOW_UNVERIFIED=1 -> bypass signature check for local testing
#   PSTN_DEFAULT_KG        -> "personal" | "work" (default "personal")
#   PSTN_WORK_PREFIXES     -> comma-separated number prefixes that map to work (e.g. "+4420,+1415")
#   INTERNAL_POST_TIMEOUT  -> seconds timeout for posting to INTERNAL_BASE (default "2.0")
# ──────────────────────────────────────────────────────────────

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
DEV_ALLOW_UNVERIFIED = os.getenv("DEV_ALLOW_UNVERIFIED", "0").strip().lower() in (
    "1", "true", "yes", "on", "y", "t"
)
PUBLIC_BASE_URL   = (os.getenv("PUBLIC_BASE_URL", "") or "").rstrip("/")
INTERNAL_BASE     = (os.getenv("INTERNAL_BASE", "http://localhost:8080")).rstrip("/")

PSTN_DEFAULT_KG       = ("work" if os.getenv("PSTN_DEFAULT_KG", "personal").lower() == "work" else "personal")
PSTN_WORK_PREFIXES    = [p.strip() for p in os.getenv("PSTN_WORK_PREFIXES", "").split(",") if p.strip()]
INTERNAL_POST_TIMEOUT = float(os.getenv("INTERNAL_POST_TIMEOUT", "2.0"))

router = APIRouter()

_httpx_client: Optional[httpx.AsyncClient] = None


def _now_ms() -> int:
    return int(time.time() * 1000)


def _normalize_e164(s: str) -> str:
    """Keep leading + and digits only."""
    s = s or ""
    return "".join(ch for ch in s if ch.isdigit() or ch == "+")


def phone_to_wa(e164: str) -> str:
    """Map a phone number to a WA (tune this to your needs)."""
    digits = _normalize_e164(e164)
    return f"ucs://wave.tp/{digits}"


def kg_for_number(e164: str) -> str:
    """Route certain prefixes to 'work', else default."""
    num = _normalize_e164(e164)
    for pref in PSTN_WORK_PREFIXES:
        if num.startswith(pref):
            return "work"
    return PSTN_DEFAULT_KG


def verify_twilio_signature(req: Request, form: Dict[str, str]) -> bool:
    """
    Twilio HMAC-SHA1 over (URL + sorted form params).
    PUBLIC_BASE_URL must match *exactly* what Twilio calls.
    """
    if DEV_ALLOW_UNVERIFIED:
        return True

    sig = req.headers.get("X-Twilio-Signature", "")
    if not TWILIO_AUTH_TOKEN or not PUBLIC_BASE_URL or not sig:
        return False

    # Build the URL Twilio used (path + optional query)
    url = f"{PUBLIC_BASE_URL}{req.url.path}"
    if req.url.query:
        url = f"{url}?{req.url.query}"

    concatenated = url + "".join(k + (form.get(k) or "") for k in sorted(form.keys()))
    digest = hmac.new(
        TWILIO_AUTH_TOKEN.encode("utf-8"),
        concatenated.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(sig, expected)


async def _get_client() -> httpx.AsyncClient:
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(timeout=INTERNAL_POST_TIMEOUT)
    return _httpx_client


async def _post_capsule(recipient_wa: str, kg: str, glyph_text: str, meta: Dict):
    """
    Fire-and-forget helper to post a simple glyph capsule into the internal GlyphNet endpoint.
    Exceptions are swallowed (webhook should not fail due to internal post).
    """
    try:
        client = await _get_client()
        await client.post(
            f"{INTERNAL_BASE}/api/glyphnet/tx",
            json={
                "recipient": recipient_wa,
                "graph": kg,
                "capsule": {"glyphs": [glyph_text]},
                "meta": meta,
            },
        )
    except Exception:
        pass


@router.post("/inbound")
async def inbound(request: Request):
    """
    Twilio 'Voice URL' webhook.
    Emits a glyph “ring” event to the appropriate WA/kg, then returns TwiML.
    """
    form_multi = await request.form()
    form = {k: form_multi.get(k) for k in form_multi.keys()}  # first value per key

    if not verify_twilio_signature(request, form):
        raise HTTPException(status_code=403, detail="bad signature")

    from_    = str(form.get("From", "") or "")
    to       = str(form.get("To", "") or "")
    call_sid = str(form.get("CallSid", "") or "")

    wa = phone_to_wa(to)
    kg = kg_for_number(to)

    meta = {
        "pstn": True,
        "call_sid": call_sid,
        "from": from_,
        "to": to,
        "t0": _now_ms(),
    }
    await _post_capsule(wa, kg, f"☎️ Incoming PSTN call from {from_}", meta)

    # Minimal TwiML (say + hangup). Replace with <Dial><Client> when bridging to WebRTC.
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Say>Thanks. The browser client will ring shortly.</Say><Hangup/></Response>"
    )
    return Response(content=xml, media_type="application/xml")


@router.post("/status")
async def status(request: Request):
    """
    Twilio 'Status Callback' webhook.
    Emits a glyph with the status of the call to the same WA/kg.
    """
    form_multi = await request.form()
    form = {k: form_multi.get(k) for k in form_multi.keys()}

    if not verify_twilio_signature(request, form):
        raise HTTPException(status_code=403, detail="bad signature")

    call_sid = str(form.get("CallSid", "") or "")
    st       = str(form.get("CallStatus", "") or "")
    to       = str(form.get("To", "") or "")

    wa = phone_to_wa(to)
    kg = kg_for_number(to)

    meta = {
        "pstn": True,
        "call_sid": call_sid,
        "status": st,
        "t0": _now_ms(),
    }
    short_sid = call_sid[-6:] if call_sid else ""
    await _post_capsule(wa, kg, f"PSTN status: {st} ({short_sid})", meta)

    return Response(status_code=204)


# ──────────────────────────────────────────────────────────────
# Lifecycle: pool the httpx client with app startup/shutdown
# Some FastAPI versions allow router-level event handlers; if not, use register_events(app).
# ──────────────────────────────────────────────────────────────

async def _voice_startup():
    # warm up the client so it's created under the app's event loop
    await _get_client()

async def _voice_shutdown():
    global _httpx_client
    if _httpx_client is not None:
        await _httpx_client.aclose()
        _httpx_client = None

# Try to attach to the router if supported by your FastAPI version
if hasattr(router, "add_event_handler"):
    router.add_event_handler("startup", _voice_startup)
    router.add_event_handler("shutdown", _voice_shutdown)

def register_events(app) -> None:
    """
    Call this from main.py if your FastAPI/APIRouter combo doesn't honor
    router event handlers:

        from backend.routes import voice
        app.include_router(voice.router, prefix="/api/voice")
        voice.register_events(app)
    """
    if hasattr(app, "add_event_handler"):
        app.add_event_handler("startup", _voice_startup)
        app.add_event_handler("shutdown", _voice_shutdown)