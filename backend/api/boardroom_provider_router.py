from __future__ import annotations

import json
import hashlib
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


class PilotDraftRequest(BaseModel):
    business_id: str = "business_not_registered"
    request: str = Field(min_length=1, max_length=12000)
    actor_scope: str = "pilot"
    approved_facts: List[Dict[str, Any]] = Field(default_factory=list)
    business_context: Dict[str, Any] = Field(default_factory=dict)
    requested_providers: List[str] = Field(default_factory=list)


class QuoteInterviewRequest(BaseModel):
    business_id: str = "business_not_registered"
    stage: str = "scope"
    user_turn: str = Field(min_length=1, max_length=6000)
    currency: str = "GBP"
    current_draft: Dict[str, Any] = Field(default_factory=dict)
    requested_providers: List[str] = Field(default_factory=list)


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


def _pilot_draft_prompt(req: PilotDraftRequest, provider_label: str) -> str:
    facts = []
    for item in req.approved_facts[:20]:
        text = str(item.get("text") or "").strip()[:2000]
        if not text:
            continue
        facts.append({
            "claim_id": str(item.get("claim_id") or "approved_fact")[:200],
            "text": text,
            "source_hash": str(item.get("source_hash") or "")[:200],
        })
    allowed_business_context = (
        "business_name",
        "legal_name",
        "website_url",
        "primary_email",
        "business_type",
        "sector",
        "sender_name",
        "sender_title",
        "sender_email",
    )
    business_context = {
        key: str(req.business_context.get(key) or "").strip()[:500]
        for key in allowed_business_context
        if str(req.business_context.get(key) or "").strip()
    }
    return (
        "You are the connected drafting model serving AION Central Pilot.\n"
        "Create the complete artifact requested by the user now. This is safe draft work only: "
        "do not claim it was sent, published, purchased, deployed, or otherwise executed.\n"
        "Do not invent company-specific facts. Use only the approved company facts and verified business "
        "identity supplied below for claims about this business, product, or sender. If essential information "
        "is absent, write a useful draft and put the gap in missing_inputs. Do not replace a known identity "
        "value with a placeholder. Omit unknown optional signature fields rather than printing a placeholder.\n"
        "Match the requested format and audience. For an email, include a useful subject line, greeting, "
        "persuasive body, clear call to action, and the verified sender/company sign-off when supplied. "
        "Return the finished artifact, "
        "not a plan explaining how to create it.\n\n"
        f"PROVIDER: {provider_label}\n"
        f"BUSINESS ID: {req.business_id}\n"
        f"ACTOR SCOPE: {req.actor_scope}\n"
        f"USER REQUEST: {req.request.strip()}\n\n"
        "APPROVED COMPANY FACTS JSON:\n"
        f"{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        "VERIFIED BUSINESS IDENTITY JSON:\n"
        f"{json.dumps(business_context, ensure_ascii=False, indent=2)}\n\n"
        "Return one JSON object with exactly these fields:\n"
        "- position: the entire finished artifact requested by the user, including every useful line of the email, "
        "document, message, or other deliverable. It must never be a label, placeholder, summary, or description "
        "such as 'complete draft' or 'draft goes here'.\n"
        "- recommendations: a JSON array of optional revision suggestions.\n"
        "- risks: a JSON array of claims or details requiring verification.\n"
        "- missing_inputs: a JSON array of essential missing inputs.\n"
        "- plan_changes: a JSON array containing the draft-only boundary or other material plan change.\n"
        "- confidence: a JSON number from 0 to 1.\n"
        "Every list must contain concise strings; use an empty list when there is nothing to report. "
        "Do not include any keys beyond those six fields."
    )


def _validate_pilot_draft_response(content: str) -> Dict[str, Any]:
    structured = _validate_board_response(content)
    draft = str(structured.get("position") or "").strip()
    placeholder = re.fullmatch(
        r"(?:complete|completed|finished|full|final|requested|reviewable|safe|client|email|document|artifact|draft|response|output|text|goes|here|ready|for|review|the|a|an|\s|[-_.:])+",
        draft,
        flags=re.IGNORECASE,
    )
    if len(draft) < 80 or placeholder:
        raise RuntimeError("incomplete_pilot_draft_response")
    return structured


def _call_connected_provider(provider_id: str, prompt: str, model_id: str | None = None) -> Dict[str, Any]:
    if provider_id == "gemma":
        return _call_ollama(prompt, model_id)
    if provider_id == "gemini":
        return _call_gemini(prompt, model_id)
    if provider_id == "claude":
        return _call_claude(prompt, model_id)
    if provider_id == "meta":
        return _call_meta(prompt, model_id)
    if provider_id in {"openai", "grok", "kimi", "mistral", "deepseek"}:
        return _call_openai_compatible(provider_id, prompt, model_id)
    raise RuntimeError("provider_call_not_implemented_yet")


_QUOTE_STAGES = {"scope", "exclusions_duration", "customer_charges", "internal_costs", "evidence", "review"}
_QUOTE_CATEGORIES = {"labour", "materials", "parking", "congestion_charge", "ulez", "supplier_subcontractor", "scaffolding", "skip_waste", "other"}


def _quote_interview_prompt(req: QuoteInterviewRequest) -> str:
    stage = req.stage if req.stage in _QUOTE_STAGES else "scope"
    return (
        "You extract one spoken turn into an in-progress customer quotation. Return JSON only.\n"
        "Remove speech fillers, repetitions and false starts. Never invent work, exclusions, time, prices, quantities, people or terms. "
        "The original customer enquiry is not supplied and must not be inferred. Use only the latest user turn and existing structured draft.\n"
        "For scope answers, turn the user's description into a short customer-friendly scope_summary plus specific scope_items. "
        "Each scope item must begin with an action such as Remove, Prepare, Supply, Install, Test, Dispose or Erect. Preserve useful sequencing and access details, "
        "but do not pad a simple job or add work the user did not state.\n"
        "A price described as cost, budget, wage, supplier cost or what someone costs belongs in internal_unit_cost. "
        "A price described as charge, sell price, quote price, customer price or total to customer belongs in customer_unit_price.\n"
        f"CURRENT STAGE: {stage}\nCURRENCY: {req.currency[:3].upper()}\n"
        f"EXISTING DRAFT JSON: {json.dumps(req.current_draft, ensure_ascii=False)[:12000]}\n"
        f"LATEST USER TURN: {json.dumps(req.user_turn, ensure_ascii=False)}\n"
        "Return exactly these keys: scope_summary (string), scope_items (array of strings), exclusions (array of strings), duration (string), "
        "charge_lines (array), terms (string), next_stage (scope|exclusions_duration|customer_charges|internal_costs|evidence|review), "
        "quote_complete_requested (boolean). Each charge line must contain exactly category, description, quantity, "
        "internal_unit_cost, customer_unit_price and person_name. Category must be labour, materials, parking, congestion_charge, "
        "ulez, supplier_subcontractor, scaffolding, skip_waste or other. Use null for every number or name not explicitly stated."
    )


def _validate_quote_interview_response(content: str) -> Dict[str, Any]:
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(content or "").strip(), flags=re.IGNORECASE)
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise RuntimeError("invalid_quote_interview_response")
    next_stage = str(parsed.get("next_stage") or "").strip()
    if next_stage not in _QUOTE_STAGES:
        raise RuntimeError("invalid_quote_interview_next_stage")
    scope_items = parsed.get("scope_items")
    exclusions = parsed.get("exclusions")
    charge_lines = parsed.get("charge_lines")
    if not isinstance(scope_items, list) or not isinstance(exclusions, list) or not isinstance(charge_lines, list):
        raise RuntimeError("invalid_quote_interview_lists")
    validated_lines: List[Dict[str, Any]] = []
    for line in charge_lines[:30]:
        if not isinstance(line, dict):
            continue
        category = str(line.get("category") or "other").strip().lower()
        if category not in _QUOTE_CATEGORIES:
            category = "other"
        numbers: Dict[str, Optional[float]] = {}
        for key in ("quantity", "internal_unit_cost", "customer_unit_price"):
            value = line.get(key)
            if value in (None, ""):
                numbers[key] = None
                continue
            try:
                number = float(str(value).replace(",", ""))
            except (TypeError, ValueError):
                raise RuntimeError(f"invalid_quote_interview_{key}")
            if number < 0 or number > 100000000:
                raise RuntimeError(f"invalid_quote_interview_{key}")
            numbers[key] = number
        validated_lines.append({
            "category": category,
            "description": str(line.get("description") or "").strip()[:500],
            "quantity": numbers["quantity"],
            "internal_unit_cost": numbers["internal_unit_cost"],
            "customer_unit_price": numbers["customer_unit_price"],
            "person_name": str(line.get("person_name") or "").strip()[:200],
        })
    return {
        "scope_summary": str(parsed.get("scope_summary") or "").strip()[:2000],
        "scope_items": [str(item).strip()[:1000] for item in scope_items[:40] if str(item).strip()],
        "exclusions": [str(item).strip()[:1000] for item in exclusions[:30] if str(item).strip()],
        "duration": str(parsed.get("duration") or "").strip()[:500],
        "charge_lines": validated_lines,
        "terms": str(parsed.get("terms") or "").strip()[:2000],
        "next_stage": next_stage,
        "quote_complete_requested": parsed.get("quote_complete_requested") is True,
    }


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


def _call_ollama(prompt: str, model_override: str | None = None) -> Dict[str, Any]:
    started = time.time()
    payload = {
        "model": str(model_override or _ollama_model()),
        "prompt": prompt,
        "stream": False,
    }
    data = _http_json(f"{_ollama_base_url()}/api/generate", payload=payload, timeout=180)
    return {
        "content": str(data.get("response") or "").strip(),
        "latency_ms": int((time.time() - started) * 1000),
    }



def _call_gemini(prompt: str, model_override: str | None = None) -> Dict[str, Any]:
    start = time.time()
    api_key = get_ai_provider_secret("gemini")
    model = str(model_override or get_ai_provider_model("gemini") or "gemini-2.5-flash")

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

def _call_openai_compatible(provider: str, prompt: str, model_override: str | None = None) -> Dict[str, Any]:
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
    model = str(model_override or get_ai_provider_model(provider) or models[provider])

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


def _call_claude(prompt: str, model_override: str | None = None) -> Dict[str, Any]:
    started = time.time()
    api_key = get_ai_provider_secret("claude")
    if not api_key:
        raise RuntimeError("missing_claude_api_key")
    model = str(model_override or get_ai_provider_model("claude") or "claude-sonnet-4-5")
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


def _call_meta(prompt: str, model_override: str | None = None) -> Dict[str, Any]:
    started = time.time()
    api_key = get_ai_provider_secret("meta")
    if not api_key:
        raise RuntimeError("missing_meta_api_key")
    model = str(model_override or get_ai_provider_model("meta") or "muse-spark-1.1")
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


@router.post("/quote-interview")
def quote_interview(req: QuoteInterviewRequest) -> Dict[str, Any]:
    providers = {item["id"]: item for item in _provider_status()}
    priority = [str(item).strip() for item in req.requested_providers if str(item).strip()] or ["gemini", "openai", "gemma"]
    attempts: List[Dict[str, str]] = []
    prompt = _quote_interview_prompt(req)
    for provider_id in priority:
        provider = providers.get(provider_id) or {}
        if provider.get("connected") is not True:
            continue
        try:
            result = _call_connected_provider(provider_id, prompt)
            extraction = _validate_quote_interview_response(str(result.get("content") or ""))
            receipt_material = json.dumps({"business_id": req.business_id, "stage": req.stage, "user_turn": req.user_turn, "provider_id": provider_id, "extraction": extraction}, ensure_ascii=False, sort_keys=True)
            return {
                "schema_version": "aion.quote_interview_turn.v1",
                "status": "extracted",
                "provider_id": provider_id,
                "provider_label": provider.get("label") or provider_id,
                "model": result.get("model") or provider.get("model"),
                "latency_ms": result.get("latency_ms"),
                "extraction": extraction,
                "receipt_hash": hashlib.sha256(receipt_material.encode("utf-8")).hexdigest(),
                "external_action_performed": False,
            }
        except Exception as exc:
            attempts.append({"provider_id": provider_id, "reason": str(exc)[:300]})
    return {
        "schema_version": "aion.quote_interview_turn.v1",
        "status": "unavailable",
        "reason": "no_provider_returned_valid_quote_extraction",
        "attempts": attempts,
        "external_action_performed": False,
    }


@router.get("/meetings/{business_id}/latest")
def latest_boardroom_meeting(business_id: str) -> Dict[str, Any]:
    path = _meeting_path(business_id)
    if not path.exists():
        return {"schema_version": "aion.boardroom_meeting_latest.v1", "status": "not_found", "item": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": "aion.boardroom_meeting_latest.v1", "status": "ok", "item": payload.get("latest")}


@router.post("/pilot-draft")
def pilot_draft(req: PilotDraftRequest) -> Dict[str, Any]:
    """Create one provider-backed draft without performing an external action."""
    providers = {item["id"]: item for item in _provider_status()}
    requested = [str(item).strip() for item in req.requested_providers if str(item).strip()]
    priority = requested or ["openai", "gemini", "claude", "grok", "kimi", "meta", "mistral", "deepseek", "gemma"]
    provider = next((providers.get(item) for item in priority if providers.get(item, {}).get("connected")), None)
    if not provider:
        return {
            "schema_version": "aion.pilot_draft_result.v1",
            "status": "unavailable",
            "reason": "no_connected_drafting_provider",
            "external_action_performed": False,
        }

    provider_id = str(provider.get("id") or "")
    prompt = _pilot_draft_prompt(req, str(provider.get("label") or provider_id))
    try:
        result = _call_connected_provider(provider_id, prompt)
        structured = _validate_pilot_draft_response(str(result.get("content") or ""))
    except urllib.error.HTTPError as exc:
        return {
            "schema_version": "aion.pilot_draft_result.v1",
            "status": "failed",
            "reason": f"http_error_{exc.code}",
            "provider_id": provider_id,
            "external_action_performed": False,
        }
    except Exception as exc:
        return {
            "schema_version": "aion.pilot_draft_result.v1",
            "status": "failed",
            "reason": str(exc),
            "provider_id": provider_id,
            "external_action_performed": False,
        }

    approved_facts = [item for item in req.approved_facts[:20] if str(item.get("text") or "").strip()]
    allowed_business_context = {
        "business_name",
        "legal_name",
        "website_url",
        "primary_email",
        "business_type",
        "sector",
        "sender_name",
        "sender_title",
        "sender_email",
    }
    business_context = {
        key: str(value).strip()[:500]
        for key, value in req.business_context.items()
        if key in allowed_business_context and str(value or "").strip()
    }
    receipt_material = json.dumps({
        "business_id": req.business_id,
        "request": req.request,
        "actor_scope": req.actor_scope,
        "provider_id": provider_id,
        "model": result.get("model") or provider.get("model"),
        "fact_ids": [str(item.get("claim_id") or "") for item in approved_facts],
        "business_context": business_context,
        "draft": structured["position"],
    }, ensure_ascii=False, sort_keys=True)
    receipt_hash = hashlib.sha256(receipt_material.encode("utf-8")).hexdigest()
    return {
        "schema_version": "aion.pilot_draft_result.v1",
        "status": "draft_ready",
        "draft": structured["position"],
        "recommendations": structured["recommendations"],
        "risks": structured["risks"],
        "missing_inputs": structured["missing_inputs"],
        "provider_id": provider_id,
        "provider_label": provider.get("label") or provider_id,
        "model": result.get("model") or provider.get("model"),
        "latency_ms": result.get("latency_ms"),
        "approved_fact_count": len(approved_facts),
        "approved_fact_ids": [str(item.get("claim_id") or "") for item in approved_facts],
        "business_context_fields_used": sorted(business_context),
        "receipt_hash": f"sha256:{receipt_hash}",
        "external_action_performed": False,
        "boundary": "draft_only_not_sent",
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
