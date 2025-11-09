# backend/routes/name_service.py
from __future__ import annotations
import os, logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
name_router = APIRouter(prefix="/api/name", tags=["NameService"])

# in-mem maps per graph (kg): label <-> wa
_DB: Dict[str, Dict[str, Dict[str, str]]] = {
    # kg: { "label2wa": {...}, "wa2label": {...} }
}

def _maps(kg: str):
    kg = (kg or "personal").lower()
    if kg not in _DB:
        _DB[kg] = {"label2wa": {}, "wa2label": {}}
    return _DB[kg]["label2wa"], _DB[kg]["wa2label"]

def _extract_token(request: Request, body: Dict[str, Any]) -> Optional[str]:
    tok = body.get("token")
    if not tok:
        tok = request.headers.get("x-agent-token") or request.headers.get("X-Agent-Token")
    if not tok:
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            tok = auth.split(" ", 1)[1]
    return tok

def _dev_ok(tok: Optional[str]) -> bool:
    return os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0").lower() in {"1","true","yes","on"} and tok in {"dev-token","local-dev"}

@name_router.post("/register")
def register(body: Dict[str, Any], request: Request):
    """
    Body: { kg: "personal"|"work", label: "kevin", wa: "ucs://realm/contact" }
    """
    tok = _extract_token(request, body)
    if not _dev_ok(tok):
        raise HTTPException(status_code=401, detail="Unauthorized")

    kg = (body.get("kg") or "personal").lower()
    label = str(body.get("label") or "").strip()
    wa = str(body.get("wa") or "").strip()
    if not label or not wa:
        raise HTTPException(status_code=400, detail="label and wa required")

    label2wa, wa2label = _maps(kg)
    label2wa[label] = wa
    wa2label[wa] = label
    return {"status":"ok","kg":kg,"label":label,"wa":wa}

@name_router.get("/resolve")
def resolve(kg: str = "personal", label: Optional[str] = None, wa: Optional[str] = None):
    """
    /resolve?kg=personal&label=kevin  -> { wa }
    /resolve?kg=work&wa=ucs://realm/x -> { label }
    """
    label2wa, wa2label = _maps(kg)
    if label:
        wa_val = label2wa.get(label)
        return {"kg":kg, "label":label, "wa": wa_val}
    if wa:
        label_val = wa2label.get(wa)
        return {"kg":kg, "wa":wa, "label": label_val}
    raise HTTPException(status_code=400, detail="pass label or wa")