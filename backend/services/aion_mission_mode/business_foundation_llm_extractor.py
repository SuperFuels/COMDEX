"""AION Phase 24B — OpenAI Business Foundation extractor.

Uses public website evidence and an OpenAI key to produce a structured
Small Business Foundation draft.

Server-side only:
- API key is read from OPENAI_API_KEY.
- No key is exposed to the frontend.
- The website scan is read-only.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.request import Request, urlopen

from backend.services.aion_mission_mode.website_foundation_extractor import (
    collect_website_evidence,
    collect_website_evidence_from_html,
    normalise_url,
)


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = os.getenv("AION_WEBSITE_SCAN_MODEL", "gpt-4.1-mini")


FOUNDATION_FIELDS = [
    "business_name",
    "industry",
    "business_type",
    "service_area",
    "products_services",
    "target_customers",
    "revenue_streams",
    "website",
    "social_accounts",
    "contact_email",
    "phone_number",
    "business_address",
    "opening_hours",
    "pricing_notes",
    "brand_notes",
    "tone_of_voice",
    "current_tools",
    "current_pain_points",
    "growth_goals",
    "reviews_or_proof",
    "extra_notes",
    "calls_to_action",
    "missing_information",
    "source_facts",
]


def _empty_foundation(url: str) -> dict[str, Any]:
    return {
        "business_name": "",
        "industry": "",
        "business_type": "unknown",
        "service_area": "",
        "products_services": "",
        "target_customers": "",
        "revenue_streams": "",
        "website": normalise_url(url),
        "social_accounts": "",
        "contact_email": "",
        "phone_number": "",
        "business_address": "",
        "opening_hours": "",
        "pricing_notes": "",
        "brand_notes": "",
        "tone_of_voice": "",
        "current_tools": "Website scan",
        "current_pain_points": "",
        "growth_goals": "",
        "reviews_or_proof": "",
        "extra_notes": "",
        "calls_to_action": "",
        "missing_information": "",
        "source_facts": "",
    }


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def normalise_foundation_json(raw: dict[str, Any], url: str) -> dict[str, str]:
    foundation = _empty_foundation(url)

    for field in FOUNDATION_FIELDS:
        if field in raw:
            foundation[field] = _coerce_text(raw[field])

    value = foundation.get("business_type", "unknown").strip().lower()
    if value not in {"services", "products", "both", "unknown"}:
        value = "unknown"
    foundation["business_type"] = value

    foundation["website"] = foundation.get("website") or normalise_url(url)
    return foundation


def extract_json_object(text: str) -> dict[str, Any]:
    value = str(text or "").strip()

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", value)
    if not match:
        raise ValueError("No JSON object returned by model")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON was not an object")
    return parsed


def build_extraction_prompt(evidence: dict[str, Any]) -> str:
    return f"""
You are extracting a business foundation from public website evidence.

Return ONLY valid JSON. Do not include markdown.

Rules:
- Do not guess facts that are not supported by evidence.
- Use source_facts to quote or summarize the evidence you relied on.
- If unknown, use an empty string or "unknown" for business_type.
- business_type must be one of: services, products, both, unknown.
- Keep products_services rich and detailed.
- Capture contact details, address, pricing, services/products, social links, reviews/proof, CTAs, tone, trust markers and missing information.
- This output will pre-fill a user-editable onboarding form.

JSON fields:
{json.dumps(FOUNDATION_FIELDS, indent=2)}

Website evidence:
{json.dumps(evidence, ensure_ascii=False, indent=2)}
""".strip()


def call_openai_for_foundation(
    evidence: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str | None = None,
    transport=None,
) -> dict[str, Any]:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    chosen_model = model or DEFAULT_MODEL
    prompt = build_extraction_prompt(evidence)

    payload = {
        "model": chosen_model,
        "input": [
            {
                "role": "system",
                "content": "You extract structured business foundations from website evidence and return strict JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.1,
    }

    if transport is not None:
        response_payload = transport(payload)
    else:
        request = Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=45) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

    # Responses API usually returns output text in output[].content[].text.
    output_text = response_payload.get("output_text")
    if not output_text:
        output_text_parts: list[str] = []
        for item in response_payload.get("output", []) or []:
            for content in item.get("content", []) or []:
                if "text" in content:
                    output_text_parts.append(str(content["text"]))
        output_text = "\n".join(output_text_parts)

    if not output_text:
        raise ValueError("OpenAI response did not contain output text")

    return extract_json_object(output_text)


def scan_website_with_openai(
    url: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    transport=None,
    timeout_seconds: int = 12,
) -> dict[str, Any]:
    target = normalise_url(url)
    evidence = collect_website_evidence(target, timeout_seconds=timeout_seconds)
    raw_foundation = call_openai_for_foundation(
        evidence,
        api_key=api_key,
        model=model,
        transport=transport,
    )

    foundation = normalise_foundation_json(raw_foundation, target)

    return {
        "ok": True,
        "url": target,
        "extracted_fields": foundation,
        "evidence": evidence,
        "source_facts": foundation.get("source_facts", ""),
        "warnings": foundation.get("missing_information", ""),
        "provider": "openai",
        "model": model or DEFAULT_MODEL,
        "live_external_side_effect": False,
    }


def scan_html_with_openai_for_tests(
    url: str,
    html: str,
    *,
    transport,
) -> dict[str, Any]:
    target = normalise_url(url)
    evidence = collect_website_evidence_from_html(target, html)
    raw_foundation = call_openai_for_foundation(evidence, api_key="test-key", transport=transport)
    foundation = normalise_foundation_json(raw_foundation, target)
    return {
        "ok": True,
        "url": target,
        "extracted_fields": foundation,
        "evidence": evidence,
        "provider": "openai",
        "live_external_side_effect": False,
    }
