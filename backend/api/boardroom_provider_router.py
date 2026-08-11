from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.modules.vault.ai_provider_key_store import (
    get_ai_provider_model,
    get_ai_provider_public_record,
    get_ai_provider_secret,
)


router = APIRouter(prefix="/api/boardroom", tags=["boardroom-providers"])
_MEETING_ROOT = Path(__file__).resolve().parents[2] / ".runtime" / "local_node" / "boardroom_meetings"


class BoardroomAskRequest(BaseModel):
    business_id: str = "business_not_registered"
    session_type: str = "business_assessment"
    context_packet: Dict[str, Any] = Field(default_factory=dict)
    founder_feedback: Dict[str, Any] = Field(default_factory=dict)
    requested_providers: List[str] = Field(default_factory=lambda: [
        "openai",
        "claude",
        "gemini",
        "grok",
        "kimi",
        "meta",
        "mistral",
        "deepseek",
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
    vision_receipt = {"openai", "claude", "gemini", "grok", "kimi", "gemma", "meta", "mistral"}
    records = [gemma] + [
        {**get_ai_provider_public_record(provider), "mode": "api_key"}
        for provider in ("openai", "claude", "gemini", "grok", "kimi", "meta", "mistral", "deepseek")
    ]
    for item in records:
        provider = item.get("id")
        item["capabilities"] = {
            "boardroom": True,
            "receipt_vision": provider in vision_receipt,
        }
        item["capability_note"] = (
            "Boardroom ready; receipt vision available when the selected model accepts images."
            if provider in vision_receipt else
            "Boardroom ready; receipt reconciliation unavailable because no verified image-input API is exposed."
        )
    return records


def _compact_canonical_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the Board's highest-authority evidence ahead of the prompt limit."""
    if not isinstance(context, dict):
        return {}

    identity = context.get("business_identity") or {}
    map_projection = context.get("business_map_projection") or {}
    function_models = context.get("function_models") or {}
    finance = function_models.get("finance") or {}
    statements = finance.get("financial_statements") or {}
    operating = context.get("operating_model") or function_models.get("operating_model") or {}
    departments = context.get("department_intelligence") or {}

    department_summary: Dict[str, Any] = {}
    for name, record in departments.items():
        if not isinstance(record, dict):
            continue
        summary = {
            "status": record.get("status"),
            "boardroom_summary": record.get("boardroom_summary"),
        }
        metrics = record.get("metrics")
        if isinstance(metrics, dict):
            summary["metrics"] = metrics
        discovery = record.get("discovery")
        if isinstance(discovery, dict):
            summary["discovery"] = {
                key: discovery.get(key)
                for key in ("status", "completed", "required", "missing", "summary")
                if key in discovery
            }
        department_summary[str(name)] = {key: value for key, value in summary.items() if value not in (None, {}, [])}

    authoritative_metrics: Dict[str, Any] = {}
    for key, record in (finance.get("authoritative_metrics") or {}).items():
        if isinstance(record, dict):
            authoritative_metrics[str(key)] = {
                field: record.get(field)
                for field in ("value", "verification", "source", "calculation")
                if record.get(field) is not None
            }
        else:
            authoritative_metrics[str(key)] = record

    facts: List[Dict[str, Any]] = []
    for fact in map_projection.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        field = str(fact.get("field") or "")
        # Detailed accepted accounting values are represented more clearly by
        # authoritative_metrics and the P&L below.
        if field.startswith("external_data."):
            continue
        facts.append({
            key: fact.get(key)
            for key in ("field", "value", "function", "verification_status", "classification")
            if fact.get(key) is not None
        })

    operating_summary = {
        key: operating.get(key)
        for key in (
            "model_status",
            "revision",
            "currency",
            "offerings",
            "customer_terms",
            "payment_terms",
            "pricing_rules",
            "financial_targets",
            "capacity_model",
            "labour_resources",
            "unit_economics",
            "overheads",
        )
        if operating.get(key) not in (None, [], {})
    }

    return {
        "schema_version": "aion.boardroom_provider_context.compact.v1",
        "business_id": context.get("business_id"),
        "generated_at": context.get("generated_at"),
        "persistent_truth_source": context.get("persistent_truth_source"),
        "business_identity": {
            key: identity.get(key)
            for key in (
                "trading_name", "legal_name", "business_type", "sector", "stage",
                "country", "region", "city", "currency", "website_url", "owner",
            )
            if identity.get(key) is not None
        },
        "source_revisions": context.get("source_revisions") or {},
        "business_map": {
            "revision": map_projection.get("revision"),
            "facts": facts,
            "assumptions": map_projection.get("assumptions") or [],
            "unknowns": map_projection.get("unknowns") or [],
            "conflicts": map_projection.get("conflicts") or [],
        },
        "department_intelligence": department_summary,
        "finance": {
            "model_status": finance.get("model_status"),
            "revision": finance.get("revision"),
            "reporting_period": finance.get("reporting_period"),
            "authoritative_metrics": authoritative_metrics,
            "profit_and_loss": statements.get("profit_and_loss") or {},
            "cashflow_model": finance.get("cashflow_model") or {},
            "statement_quality": finance.get("statement_quality") or {},
            "missing_information": finance.get("missing_information") or [],
        },
        "operating_model": operating_summary,
        "execution_boundary": context.get("execution_boundary") or {},
    }


def _provider_context_packet(context_packet: Dict[str, Any]) -> Dict[str, Any]:
    packet = dict(context_packet or {})
    canonical = packet.get("canonical_context_envelope")
    if isinstance(canonical, dict):
        # The full canonical envelope can exceed 300 KB. A raw string slice
        # silently drops later Finance/HR/Operations evidence. Replace it with
        # a compact authority-first view before serialising the prompt.
        packet["canonical_context_envelope"] = _compact_canonical_context(canonical)
    return packet


def _board_prompt(req: BoardroomAskRequest, provider_label: str) -> str:
    context_packet = _provider_context_packet(req.context_packet)
    return (
        "You are acting as one connected model inside the AION Boardroom.\n"
        "Do not pretend to be another provider. Answer only as your own model/provider.\n\n"
        f"PROVIDER ROLE: {provider_label}\n"
        f"SESSION TYPE: {req.session_type}\n"
        f"BUSINESS ID: {req.business_id}\n"
        f"OBJECTIVE: {req.objective}\n\n"
        "BUSINESS CONTEXT PACKET JSON:\n"
        f"{json.dumps(context_packet, ensure_ascii=False, indent=2)[:24000]}\n\n"
        "FOUNDER FEEDBACK JSON:\n"
        f"{json.dumps(req.founder_feedback, ensure_ascii=False, indent=2)[:6000]}\n\n"
        "Return JSON only. Keep the entire response below 1,200 words. Exact schema: "
        '{"position":"string","recommendations":["string"],"risks":["string"],'
        '"missing_inputs":["string"],"plan_changes":["string"],"confidence":0.0}. '
        "Every list must be a flat list of concise strings. Do not nest recommendations by role.\n"
    )


def _validate_board_response(content: str) -> Dict[str, Any]:
    raw = str(content or "").strip()
    if raw.startswith("```"):
        raw = raw.removeprefix("```json").removeprefix("```").strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"invalid_structured_response_json:{type(exc).__name__}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("invalid_structured_response_not_object")
    if not isinstance(parsed.get("position"), str) or not parsed.get("position", "").strip():
        raise RuntimeError("invalid_structured_response_position")
    for key in ("recommendations", "risks", "missing_inputs", "plan_changes"):
        value = parsed.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise RuntimeError(f"invalid_structured_response_{key}")
    confidence = parsed.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise RuntimeError("invalid_structured_response_confidence")
    return parsed


def _meeting_path(business_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(business_id or "business")).strip(".-") or "business"
    return _MEETING_ROOT / f"{safe_id}.json"


def _persist_board_meeting(business_id: str, result: Dict[str, Any]) -> None:
    path = _meeting_path(business_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    history: List[Dict[str, Any]] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            history = list(existing.get("history") or [])
        except Exception:
            history = []
    record = {**result, "persisted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    history = [*history, record][-50:]
    payload = {"schema_version": "aion.boardroom_meeting_ledger.v1", "latest": record, "history": history}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


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

def _call_openai_compatible(provider: str, prompt: str) -> Dict[str, Any]:
    started = time.time()
    api_key = get_ai_provider_secret(provider)
    if not api_key:
        raise RuntimeError(f"missing_{provider}_api_key")
    models = {
        "openai": "gpt-4o-mini", "grok": "grok-4.5", "kimi": "kimi-k3",
        "mistral": "mistral-small-latest", "deepseek": "deepseek-v4-pro",
    }
    endpoints = {
        "openai": "https://api.openai.com/v1/chat/completions",
        "grok": "https://api.x.ai/v1/chat/completions",
        "kimi": "https://api.moonshot.ai/v1/chat/completions",
        "mistral": "https://api.mistral.ai/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/chat/completions",
    }
    model = get_ai_provider_model(provider) or models[provider]

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
        "response_format": {"type": "json_object"},
    }

    data = _http_json(
        endpoints[provider],
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


def _call_claude(prompt: str) -> Dict[str, Any]:
    started = time.time()
    api_key = get_ai_provider_secret("claude")
    if not api_key:
        raise RuntimeError("missing_claude_api_key")
    model = get_ai_provider_model("claude") or "claude-sonnet-4-5"
    data = _http_json(
        "https://api.anthropic.com/v1/messages",
        payload={
            "model": model, "max_tokens": 4096,
            "system": "You are a connected model in the AION Boardroom. Return concise JSON only.",
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "position": {"type": "string"},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "missing_inputs": {"type": "array", "items": {"type": "string"}},
                    "plan_changes": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": ["position", "recommendations", "risks", "missing_inputs", "plan_changes", "confidence"],
            }}},
        },
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=90,
    )
    content = "".join(str(item.get("text") or "") for item in data.get("content", []) if item.get("type") == "text").strip()
    return {"content": content, "latency_ms": int((time.time() - started) * 1000), "model": model}


def _call_meta(prompt: str) -> Dict[str, Any]:
    started = time.time()
    api_key = get_ai_provider_secret("meta")
    if not api_key:
        raise RuntimeError("missing_meta_api_key")
    model = get_ai_provider_model("meta") or "muse-spark-1.1"
    data = _http_json(
        "https://api.meta.ai/v1/responses",
        payload={
            "model": model, "store": False,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            "text": {"format": {"type": "json_object"}},
        },
        headers={"Authorization": f"Bearer {api_key}"}, timeout=90,
    )
    content = "".join(
        str(block.get("text") or "")
        for item in data.get("output", []) if item.get("type") == "message"
        for block in item.get("content", []) if block.get("type") == "output_text"
    ).strip()
    return {"content": content, "latency_ms": int((time.time() - started) * 1000), "model": model}


@router.get("/providers/status")
def boardroom_provider_status() -> Dict[str, Any]:
    providers = _provider_status()
    return {
        "schema_version": "aion.boardroom_provider_status.v1",
        "live_provider_registry": True,
        "providers": providers,
        "connected_count": sum(1 for p in providers if p.get("connected")),
    }


@router.get("/meetings/{business_id}/latest")
def latest_boardroom_meeting(business_id: str) -> Dict[str, Any]:
    path = _meeting_path(business_id)
    if not path.exists():
        return {"schema_version": "aion.boardroom_meeting_latest.v1", "status": "not_found", "item": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": "aion.boardroom_meeting_latest.v1", "status": "ok", "item": payload.get("latest")}


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
            elif provider_id == "gemini":
                result = _call_gemini(prompt)
            elif provider_id == "claude":
                result = _call_claude(prompt)
            elif provider_id == "meta":
                result = _call_meta(prompt)
            elif provider_id in {"openai", "grok", "kimi", "mistral", "deepseek"}:
                result = _call_openai_compatible(provider_id, prompt)
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

            structured = _validate_board_response(str(result.get("content") or ""))

            responses.append({
                "provider_id": provider_id,
                "label": provider.get("label"),
                "mode": provider.get("mode"),
                "model": result.get("model") or provider.get("model"),
                "status": "succeeded",
                "reason": None,
                "latency_ms": result.get("latency_ms"),
                "content": result.get("content"),
                "structured": structured,
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

    result = {
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
    if succeeded:
        _persist_board_meeting(req.business_id, result)
    return result
