from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.modules.vault.ai_provider_key_store import (
    get_ai_provider_model,
    get_ai_provider_public_record,
    get_ai_provider_secret,
)


router = APIRouter(prefix="/api/boardroom", tags=["boardroom-providers"])


class BoardroomAskRequest(BaseModel):
    business_id: str = "business_not_registered"
    session_type: str = "business_assessment"
    context_packet: Dict[str, Any] = Field(default_factory=dict)
    founder_feedback: Dict[str, Any] = Field(default_factory=dict)
    requested_providers: List[str] = Field(default_factory=lambda: [
        "gemma",
        "openai",
        "claude",
        "gemini",
        "grok",
    ])
    objective: str = (
        "Analyse the business context and produce a boardroom response with "
        "position, recommendations, risks, missing inputs, and confidence."
    )


def _env_present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gemma4:e2b").strip() or "gemma4:e2b"


def _http_json(
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="GET" if payload is None else "POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read().decode("utf-8", errors="replace")
        return json.loads(raw or "{}")


def _ollama_status() -> Dict[str, Any]:
    try:
        data = _http_json(f"{_ollama_base_url()}/api/tags", timeout=5)
        models = [str(item.get("name") or item.get("model") or "") for item in data.get("models", [])]
        model = _ollama_model()
        connected = any(name == model or "gemma" in name.lower() for name in models)

        return {
            "id": "gemma",
            "label": "Gemma",
            "mode": "local_ollama",
            "connected": connected,
            "model": model,
            "source": "local_ollama",
            "available_models": models,
            "reason": None if connected else "gemma_model_not_found",
        }
    except Exception as exc:
        return {
            "id": "gemma",
            "label": "Gemma",
            "mode": "local_ollama",
            "connected": False,
            "model": _ollama_model(),
            "source": "local_ollama",
            "available_models": [],
            "reason": f"ollama_unreachable: {exc}",
        }


def _provider_status() -> List[Dict[str, Any]]:
    gemma = _ollama_status()

    return [
        gemma,
        {
            **get_ai_provider_public_record("openai"),
            "mode": "api_key",
        },
        {
            **get_ai_provider_public_record("claude"),
            "mode": "api_key",
        },
        {
            **get_ai_provider_public_record("gemini"),
            "mode": "api_key",
        },
        {
            **get_ai_provider_public_record("grok"),
            "mode": "api_key",
        },
    ]


def _board_prompt(req: BoardroomAskRequest, provider_label: str) -> str:
    return (
        "You are acting as one connected model inside the AION Boardroom.\n"
        "Do not pretend to be another provider. Answer only as your own model/provider.\n\n"
        f"PROVIDER ROLE: {provider_label}\n"
        f"SESSION TYPE: {req.session_type}\n"
        f"BUSINESS ID: {req.business_id}\n"
        f"OBJECTIVE: {req.objective}\n\n"
        "BUSINESS CONTEXT PACKET JSON:\n"
        f"{json.dumps(req.context_packet, ensure_ascii=False, indent=2)[:12000]}\n\n"
        "FOUNDER FEEDBACK JSON:\n"
        f"{json.dumps(req.founder_feedback, ensure_ascii=False, indent=2)[:6000]}\n\n"
        "Return concise JSON only with keys: position, recommendations, risks, missing_inputs, plan_changes, confidence.\n"
    )


def _call_ollama(prompt: str) -> Dict[str, Any]:
    started = time.time()
    payload = {
        "model": _ollama_model(),
        "prompt": prompt,
        "stream": False,
    }
    data = _http_json(f"{_ollama_base_url()}/api/generate", payload=payload, timeout=180)
    return {
        "content": str(data.get("response") or "").strip(),
        "latency_ms": int((time.time() - started) * 1000),
    }



def _call_gemini(prompt: str) -> Dict[str, Any]:
    start = time.time()
    api_key = get_ai_provider_secret("gemini")
    model = get_ai_provider_model("gemini") or "gemini-2.5-flash"

    if not api_key:
        raise RuntimeError("missing_gemini_api_key")

    # Gemini REST generateContent endpoint.
    # Uses header key so raw keys are not placed into logs/URLs.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }

    data = _http_json(
        url,
        payload=payload,
        headers={
            "x-goog-api-key": api_key,
        },
        timeout=90,
    )

    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )

    content = "\n".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict) and part.get("text")
    ).strip()

    if not content:
        raise RuntimeError("gemini_empty_response")

    return {
        "model": model,
        "latency_ms": int((time.time() - start) * 1000),
        "content": content,
    }

def _call_openai(prompt: str) -> Dict[str, Any]:
    started = time.time()
    api_key = get_ai_provider_secret("openai")
    model = get_ai_provider_model("openai") or "gpt-4o-mini"

    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "You are a connected model in the AION Boardroom. Return concise JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    data = _http_json(
        "https://api.openai.com/v1/chat/completions",
        payload=payload,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=90,
    )

    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    return {
        "content": str(content or "").strip(),
        "latency_ms": int((time.time() - started) * 1000),
        "model": model,
    }


@router.get("/providers/status")
def boardroom_provider_status() -> Dict[str, Any]:
    providers = _provider_status()
    return {
        "schema_version": "aion.boardroom_provider_status.v1",
        "live_provider_registry": True,
        "providers": providers,
        "connected_count": sum(1 for p in providers if p.get("connected")),
    }


@router.post("/ask")
def boardroom_ask(req: BoardroomAskRequest) -> Dict[str, Any]:
    providers = {item["id"]: item for item in _provider_status()}
    responses: List[Dict[str, Any]] = []

    for provider_id in req.requested_providers:
        provider = providers.get(provider_id)

        if not provider:
            responses.append({
                "provider_id": provider_id,
                "status": "unavailable",
                "reason": "unknown_provider",
                "content": None,
            })
            continue

        if not provider.get("connected"):
            responses.append({
                "provider_id": provider_id,
                "label": provider.get("label"),
                "mode": provider.get("mode"),
                "status": "unavailable",
                "reason": provider.get("reason") or "not_connected",
                "content": None,
            })
            continue

        prompt = _board_prompt(req, provider.get("label") or provider_id)

        try:
            if provider_id == "gemma":
                result = _call_ollama(prompt)
            elif provider_id == "openai":
                result = _call_openai(prompt)
            elif provider_id == "gemini":
                result = _call_gemini(prompt)
            else:
                responses.append({
                    "provider_id": provider_id,
                    "label": provider.get("label"),
                    "mode": provider.get("mode"),
                    "status": "unavailable",
                    "reason": "provider_call_not_implemented_yet",
                    "content": None,
                })
                continue

            responses.append({
                "provider_id": provider_id,
                "label": provider.get("label"),
                "mode": provider.get("mode"),
                "model": result.get("model") or provider.get("model"),
                "status": "succeeded",
                "reason": None,
                "latency_ms": result.get("latency_ms"),
                "content": result.get("content"),
            })

        except urllib.error.HTTPError as exc:
            responses.append({
                "provider_id": provider_id,
                "label": provider.get("label"),
                "mode": provider.get("mode"),
                "status": "failed",
                "reason": f"http_error_{exc.code}",
                "content": None,
            })
        except Exception as exc:
            responses.append({
                "provider_id": provider_id,
                "label": provider.get("label"),
                "mode": provider.get("mode"),
                "status": "failed",
                "reason": str(exc),
                "content": None,
            })

    succeeded = [r for r in responses if r.get("status") == "succeeded"]

    return {
        "schema_version": "aion.boardroom_ask_result.v1",
        "live_provider_fanout": bool(succeeded),
        "simulated_responses": False,
        "provider_count": len(responses),
        "succeeded_count": len(succeeded),
        "responses": responses,
        "missing_or_unavailable": [
            r for r in responses if r.get("status") != "succeeded"
        ],
        "synthesis_pending": True,
        "note": "This endpoint calls only connected providers. Missing providers return unavailable and do not generate fake answers.",
    }
