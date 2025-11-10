# backend/routes/voice_flask.py
import os, time, hmac, hashlib, base64, requests
from flask import Blueprint, request, abort, Response

bp = Blueprint("voice", __name__)
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN","")
PUBLIC_BASE_URL   = (os.getenv("PUBLIC_BASE_URL","") or "").rstrip("/")
INTERNAL_BASE     = (os.getenv("INTERNAL_BASE","http://localhost:8080")).rstrip("/")

def phone_to_wa(e164: str) -> str:
    digits = "".join(ch for ch in e164 if ch.isdigit() or ch == "+")
    return f"ucs://wave.tp/{digits}"

def verify_twilio_signature(req) -> bool:
    sig = req.headers.get("X-Twilio-Signature","")
    if not (TWILIO_AUTH_TOKEN and PUBLIC_BASE_URL and sig):
        return False
    url = f"{PUBLIC_BASE_URL}{request.path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    params = request.form.to_dict(flat=True)
    concatenated = url + "".join(k + params[k] for k in sorted(params.keys()))
    expected = base64.b64encode(hmac.new(TWILIO_AUTH_TOKEN.encode(), concatenated.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(sig, expected)

@bp.route("/inbound", methods=["POST"])
def inbound():
    if not verify_twilio_signature(request): abort(403)
    from_ = request.form.get("From","")
    to    = request.form.get("To","")
    sid   = request.form.get("CallSid","")
    wa, kg = phone_to_wa(to), "personal"
    try:
        requests.post(f"{INTERNAL_BASE}/api/glyphnet/tx", json={
            "recipient": wa, "graph": kg,
            "capsule": { "glyphs": [f"☎️ Incoming PSTN call from {from_}"] },
            "meta": { "pstn": True, "call_sid": sid, "from": from_, "to": to, "t0": int(time.time()*1000) }
        }, timeout=3)
    except Exception: pass
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Thanks. The browser client will ring shortly.</Say><Hangup/></Response>'
    return Response(xml, mimetype="application/xml")

@bp.route("/status", methods=["POST"])
def status():
    if not verify_twilio_signature(request): abort(403)
    sid = request.form.get("CallSid",""); st = request.form.get("CallStatus",""); to = request.form.get("To","")
    wa, kg = phone_to_wa(to), "personal"
    try:
        requests.post(f"{INTERNAL_BASE}/api/glyphnet/tx", json={
            "recipient": wa, "graph": kg,
            "capsule": { "glyphs": [f"PSTN status: {st} ({sid[-6:]})"] },
            "meta": { "pstn": True, "call_sid": sid, "status": st, "t0": int(time.time()*1000) }
        }, timeout=3)
    except Exception: pass
    return ("", 204)