# backend/api/rtc_api.py
from fastapi import APIRouter
import os

router = APIRouter(prefix="/api/rtc", tags=["rtc"])

@router.get("/ice")
def get_ice():
    # Always provide STUN
    ice = [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:global.stun.twilio.com:3478"},
    ]

    # Optional TURN (enable via env)
    # Single URI form: turn:host:3478?transport=udp  OR  turns:host:5349?transport=tcp
    turn_uri = os.getenv("TURN_URI")
    turn_user = os.getenv("TURN_USER")
    turn_cred = os.getenv("TURN_CREDENTIAL")

    if turn_uri and turn_user and turn_cred:
        ice.append({"urls": [turn_uri], "username": turn_user, "credential": turn_cred})

    return {"iceServers": ice, "ttl": 3600}