# backend/routes/voice.py
import os, time, hmac, hashlib, base64
from typing import Dict
import requests
from fastapi import APIRouter, Request, HTTPException, Response

# ENV you need to set in your cloud server:
#   TWILIO_AUTH_TOKEN  -> for X-Twilio-Signature validation
#   PUBLIC_BASE_URL    -> your public https base (e.g. https://<your-domain>)
#   INTERNAL_BASE      -> where your app accepts /api/glyphnet/tx (default localhost:8080)

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
PUBLIC_BASE_URL   = (os.getenv("PUBLIC_BASE_URL", "") or "").rstrip("/")
INTERNAL_BASE     = (os.getenv("INTERNAL_BASE", "http://localhost:8080")).rstrip("/")

router = APIRouter()

def phone_to_wa(e164: str) -> str:
    """Map a phone number to a WA (tune this to your needs)."""
    digits = "".join(ch for ch in e164 if ch.isdigit() or ch == "+")
    return f"ucs://wave.tp/{digits}"

def verify_twilio_signature(req: Request, form: Dict[str, str]) -> bool:
    """
    Twilio HMAC-SHA1 over (URL + sorted form params).
    Make sure PUBLIC_BASE_URL matches exactly what Twilio calls.
    """
    sig = req.headers.get("X-Twilio-Signature", "")
    if not TWILIO_AUTH_TOKEN or not PUBLIC_BASE_URL or not sig:
        return False

    # Use the exact path Twilio hit; prepend PUBLIC_BASE_URL
    url = f"{PUBLIC_BASE_URL}{req.url.path}"
    # If you set query parameters in the Console URL, include them here too:
    if req.url.query:
        url = f"{url}?{req.url.query}"

    concatenated = url + "".join(k + form[k] for k in sorted(form.keys()))
    digest = hmac.new(
        TWILIO_AUTH_TOKEN.encode("utf-8"),
        concatenated.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    # constant-time compare
    return hmac.compare_digest(sig, expected)

@router.post("/inbound")
async def inbound(request: Request):
    form_multi = await request.form()
    # Take the first value for each key (Twilio sends form-encoded)
    form = {k: form_multi.get(k) for k in form_multi.keys()}

    if not verify_twilio_signature(request, form):
        raise HTTPException(status_code=403, detail="bad signature")

    from_    = str(form.get("From", ""))
    to       = str(form.get("To", ""))
    call_sid = str(form.get("CallSid", ""))

    wa  = phone_to_wa(to)
    kg  = "personal"  # choose how you want to map numbers → graph

    # Post a simple “ring” event into the thread (stub)
    try:
        requests.post(
            f"{INTERNAL_BASE}/api/glyphnet/tx",
            json={
                "recipient": wa,
                "graph": kg,
                "capsule": { "glyphs": [f"☎️ Incoming PSTN call from {from_}"] },
                "meta": { "pstn": True, "call_sid": call_sid, "from": from_, "to": to, "t0": int(time.time()*1000) },
            },
            timeout=3,
        )
    except Exception:
        pass

    # Minimal TwiML for now (say+hang up). Replace with <Dial><Client> later.
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Say>Thanks. The browser client will ring shortly.</Say><Hangup/></Response>"
    )
    return Response(content=xml, media_type="application/xml")

@router.post("/status")
async def status(request: Request):
    form_multi = await request.form()
    form = {k: form_multi.get(k) for k in form_multi.keys()}

    if not verify_twilio_signature(request, form):
        raise HTTPException(status_code=403, detail="bad signature")

    call_sid = str(form.get("CallSid", ""))
    status   = str(form.get("CallStatus", ""))
    to       = str(form.get("To", ""))

    wa = phone_to_wa(to)
    kg = "personal"

    try:
        requests.post(
            f"{INTERNAL_BASE}/api/glyphnet/tx",
            json={
                "recipient": wa,
                "graph": kg,
                "capsule": { "glyphs": [f"PSTN status: {status} ({call_sid[-6:]})"] },
                "meta": { "pstn": True, "call_sid": call_sid, "status": status, "t0": int(time.time()*1000) },
            },
            timeout=3,
        )
    except Exception:
        pass

    return Response(status_code=204)