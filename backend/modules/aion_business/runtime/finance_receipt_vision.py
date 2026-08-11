"""Structured, suggestion-only reading for receipts and finance documents."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from time import monotonic
from typing import Any


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


RECEIPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string", "enum": ["receipt", "supplier_invoice", "sales_invoice", "credit_note", "expense_claim", "other"]},
        "supplier": {"type": ["string", "null"]},
        "document_date": {"type": ["string", "null"]},
        "currency": {"type": ["string", "null"]},
        "total": {"type": ["number", "null"]},
        "net": {"type": ["number", "null"]},
        "tax": {"type": ["number", "null"]},
        "tip": {"type": ["number", "null"]},
        "invoice_number": {"type": ["string", "null"]},
        "due_date": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "payment_method": {"type": ["string", "null"]},
        "card_last_four": {"type": ["string", "null"]},
        "merchant_tax_id": {"type": ["string", "null"]},
        "merchant_address": {"type": ["string", "null"]},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": ["number", "null"]},
                    "unit_price": {"type": ["number", "null"]},
                    "total": {"type": ["number", "null"]},
                    "tax_rate": {"type": ["number", "null"]},
                },
                "required": ["description", "quantity", "unit_price", "total", "tax_rate"],
            },
        },
        "category_signals": {
            "type": "array",
            "items": {"type": "string", "enum": ["materials", "tools_equipment", "office", "software", "telecoms", "fuel", "vehicle", "travel", "accommodation", "meal", "business_hospitality", "alcohol", "professional_fees", "personal", "mixed", "other"]},
        },
        "primary_category": {"type": ["string", "null"], "enum": ["materials", "tools_equipment", "office", "software", "telecoms", "fuel", "vehicle", "travel", "accommodation", "meal", "professional_fees", "personal", "mixed", "other", None]},
        "primary_category_confidence": {"type": "number"},
        "field_confidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "supplier": {"type": "number"}, "document_date": {"type": "number"},
                "currency": {"type": "number"}, "total": {"type": "number"},
                "net": {"type": "number"}, "tax": {"type": "number"},
                "invoice_number": {"type": "number"}, "description": {"type": "number"},
                "payment_method": {"type": "number"}, "line_items": {"type": "number"},
            },
            "required": ["supplier", "document_date", "currency", "total", "net", "tax", "invoice_number", "description", "payment_method", "line_items"],
        },
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "document_type", "supplier", "document_date", "currency", "total", "net", "tax", "tip",
        "invoice_number", "due_date", "description", "payment_method", "card_last_four",
        "merchant_tax_id", "merchant_address", "line_items", "category_signals", "primary_category",
        "primary_category_confidence", "field_confidence",
        "uncertainties",
    ],
}


class FinanceReceiptVisionReader:
    """Read visible facts without making accounting or tax decisions."""

    def __init__(self, *, client: Any | None = None, model: str | None = None, provider: str | None = None) -> None:
        self.model = model
        self.provider = provider or os.getenv("AION_RECEIPT_VISION_PROVIDER", "auto")
        self._client = client

    def read(self, path: Path, *, expected_document_type: str = "receipt") -> dict[str, Any]:
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES | {".pdf"}:
            raise ValueError("finance_document_not_supported_by_reader")
        if suffix == ".heic":
            with tempfile.TemporaryDirectory(prefix="tessaris-receipt-") as directory:
                converted = Path(directory) / "receipt.jpg"
                process = subprocess.run(
                    ["/usr/bin/sips", "-s", "format", "jpeg", str(path), "--out", str(converted)],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                if process.returncode != 0 or not converted.exists():
                    raise RuntimeError("receipt_heic_conversion_failed")
                return self.read(converted, expected_document_type=expected_document_type)
        raw = path.read_bytes()
        encoded = base64.b64encode(raw).decode("ascii")
        instructions = (
            "Read only facts visibly supported by this finance document. Do not guess missing values. "
            "Use ISO YYYY-MM-DD dates where the date is clear. Currency must be a three-letter ISO code. "
            "Amounts are positive document amounts. Keep total, net, tax and tip separate. "
            "Category signals describe visible goods or merchant context only; they are not tax or business-purpose decisions. "
            "Choose one primary visible expense category when the purchased items support it, otherwise use null. "
            "A restaurant receipt cannot prove business hospitality, and fuel cannot prove business mileage. "
            "Mark personal or mixed only where the visible items support it. Return uncertainty whenever text is unclear."
        )
        prompt = (
            f"{instructions}\n\nExtract this document into the supplied schema. The uploader labelled it "
            f"{expected_document_type!r}; correct that label only if the document visibly shows another type."
        )
        failures: list[str] = []
        for provider in self._provider_chain():
            try:
                result = self._read_provider(provider, path, raw, encoded, prompt, instructions)
                result["facts"] = self._validated_facts(result.get("facts"))
                result["fallback_attempts"] = failures
                return result
            except Exception as exc:
                failures.append(f"{provider}:{type(exc).__name__}")
                if self.provider.strip().lower() != "auto" or self._client is not None:
                    raise
        raise RuntimeError("receipt_vision_all_configured_providers_failed:" + ",".join(failures))

    def _read_provider(
        self, provider: str, path: Path, raw: bytes, encoded: str, prompt: str, instructions: str,
    ) -> dict[str, Any]:
        if provider == "gemini":
            return self._read_gemini(path, raw, encoded, prompt)
        if provider == "openai":
            return self._read_openai(path, path.suffix.lower(), encoded, prompt, instructions)
        if provider == "claude":
            return self._read_claude(path, raw, encoded, prompt)
        if provider == "grok":
            return self._read_grok(path, raw, prompt)
        if provider == "kimi":
            return self._read_kimi(path, raw, prompt)
        if provider == "gemma":
            return self._read_local_gemma(path, raw, prompt)
        if provider == "meta":
            return self._read_meta(path, raw, prompt)
        if provider == "mistral":
            return self._read_mistral(path, raw, prompt)
        if provider == "deepseek":
            raise RuntimeError("receipt_vision_provider_has_no_verified_image_input")
        raise ValueError(f"receipt_vision_provider_unknown:{provider}")

    def _read_openai(self, path: Path, suffix: str, encoded: str, prompt: str, instructions: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("openai")
        if self._client is None and not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=api_key, timeout=60.0)
        if suffix == ".pdf":
            media = {
                "type": "input_file", "filename": path.name,
                "file_data": f"data:application/pdf;base64,{encoded}",
            }
        else:
            mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            media = {
                "type": "input_image", "image_url": f"data:{mime};base64,{encoded}",
                "detail": "high",
            }

        model = self.model or os.getenv("AION_RECEIPT_VISION_MODEL") or get_ai_provider_model("openai") or "gpt-4.1-mini"
        started = monotonic()
        response = self._client.responses.create(
            model=model,
            instructions=instructions,
            input=[{"role": "user", "content": [media, {"type": "input_text", "text": prompt}]}],
            text={"format": {"type": "json_schema", "name": "finance_document_extraction", "strict": True, "schema": RECEIPT_SCHEMA}},
            max_output_tokens=2500,
            store=False,
        )
        if getattr(response, "status", None) == "incomplete":
            raise RuntimeError("receipt_vision_response_incomplete")
        output_text = str(getattr(response, "output_text", "") or "").strip()
        if not output_text:
            raise RuntimeError("receipt_vision_empty_response")
        payload = json.loads(output_text)
        usage = getattr(response, "usage", None)
        return {
            "facts": payload,
            "provider": "openai",
            "model": model,
            "response_id": getattr(response, "id", None),
            "latency_ms": round((monotonic() - started) * 1000),
            "usage": usage.model_dump() if hasattr(usage, "model_dump") else {},
            "source_sent_externally": True,
            "provider_storage_requested": False,
        }

    def _read_gemini(self, path: Path, raw: bytes, encoded: str, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("gemini")
        if not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        if len(raw) > 18 * 1024 * 1024:
            raise ValueError("finance_document_too_large_for_inline_reader")
        model = os.getenv("AION_RECEIPT_GEMINI_MODEL") or get_ai_provider_model("gemini") or "gemini-2.5-flash"
        mime = mimetypes.guess_type(path.name)[0] or ("application/pdf" if path.suffix.lower() == ".pdf" else "image/jpeg")
        payload = {
            "contents": [{"role": "user", "parts": [
                {"inlineData": {"mimeType": mime, "data": encoded}}, {"text": prompt},
            ]}],
            "generationConfig": {
                "responseMimeType": "application/json", "responseJsonSchema": RECEIPT_SCHEMA,
                "temperature": 0.0, "maxOutputTokens": 2500,
            },
        }
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key, "User-Agent": "Tessaris-Finance-Reader/1.0"},
        )
        started = monotonic()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"gemini_receipt_reader_http_{exc.code}:{detail}") from exc
        candidates = body.get("candidates") or []
        parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
        output_text = "".join(str(item.get("text") or "") for item in parts).strip()
        if not output_text:
            raise RuntimeError("receipt_vision_empty_response")
        return {
            "facts": json.loads(output_text), "provider": "gemini", "model": model,
            "response_id": body.get("responseId"), "latency_ms": round((monotonic() - started) * 1000),
            "usage": body.get("usageMetadata") or {}, "source_sent_externally": True,
            "provider_storage_requested": False,
        }

    def _read_claude(self, path: Path, raw: bytes, encoded: str, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("claude")
        if not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        model = self.model or os.getenv("AION_RECEIPT_CLAUDE_MODEL") or get_ai_provider_model("claude")
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        media_type = "document" if path.suffix.lower() == ".pdf" else "image"
        content = [{"type": media_type, "source": {"type": "base64", "media_type": mime, "data": encoded}}, {"type": "text", "text": prompt}]
        payload = {
            "model": model, "max_tokens": 2500,
            "messages": [{"role": "user", "content": content}],
            "output_config": {"format": {"type": "json_schema", "schema": RECEIPT_SCHEMA}},
        }
        started = monotonic()
        body = self._post_json(
            "https://api.anthropic.com/v1/messages", payload,
            {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )
        if body.get("stop_reason") in {"max_tokens", "refusal"}:
            raise RuntimeError(f"claude_receipt_reader_stopped:{body.get('stop_reason')}")
        output_text = "".join(str(item.get("text") or "") for item in body.get("content", []) if item.get("type") == "text").strip()
        return self._result("claude", model, output_text, body.get("id"), body.get("usage"), started, external=True)

    def _read_grok(self, path: Path, raw: bytes, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("grok")
        if not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        model = self.model or os.getenv("AION_RECEIPT_GROK_MODEL") or get_ai_provider_model("grok")
        image_raw, mime = self._raster_image(path, raw)
        encoded = base64.b64encode(image_raw).decode("ascii")
        payload = {
            "model": model, "store": False, "max_output_tokens": 2500,
            "input": [{"role": "user", "content": [
                {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}", "detail": "high"},
                {"type": "input_text", "text": prompt},
            ]}],
            "text": {"format": {"type": "json_schema", "name": "finance_document_extraction", "strict": True, "schema": RECEIPT_SCHEMA}},
        }
        started = monotonic()
        body = self._post_json("https://api.x.ai/v1/responses", payload, {"Authorization": f"Bearer {api_key}"})
        output_text = self._responses_output_text(body)
        return self._result("grok", model, output_text, body.get("id"), body.get("usage"), started, external=True)

    def _read_kimi(self, path: Path, raw: bytes, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("kimi")
        if not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        model = self.model or os.getenv("AION_RECEIPT_KIMI_MODEL") or get_ai_provider_model("kimi") or "kimi-k3"
        image_raw, mime = self._raster_image(path, raw)
        encoded = base64.b64encode(image_raw).decode("ascii")
        schema_prompt = prompt + "\nReturn JSON only matching this schema:\n" + json.dumps(RECEIPT_SCHEMA, separators=(",", ":"))
        payload = {
            "model": model, "temperature": 0, "max_tokens": 2500,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                {"type": "text", "text": schema_prompt},
            ]}],
            "response_format": {"type": "json_object"},
        }
        started = monotonic()
        body = self._post_json("https://api.moonshot.ai/v1/chat/completions", payload, {"Authorization": f"Bearer {api_key}"})
        choices = body.get("choices") or []
        output_text = str(((choices[0].get("message") or {}).get("content") or "") if choices else "").strip()
        return self._result("kimi", model, output_text, body.get("id"), body.get("usage"), started, external=True)

    def _read_local_gemma(self, path: Path, raw: bytes, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model

        model = self.model or os.getenv("AION_RECEIPT_GEMMA_MODEL") or get_ai_provider_model("gemma") or "gemma4:e2b"
        base_url = os.getenv("AION_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        image_raw, _ = self._raster_image(path, raw)
        show = self._post_json(f"{base_url}/api/show", {"model": model}, {})
        if "vision" not in set(show.get("capabilities") or []):
            raise RuntimeError("receipt_vision_model_lacks_vision")
        payload = {
            "model": model, "stream": False, "format": RECEIPT_SCHEMA,
            "messages": [{"role": "user", "content": prompt + "\nReturn only the requested JSON.", "images": [base64.b64encode(image_raw).decode("ascii")]}],
            "options": {"temperature": 0},
        }
        started = monotonic()
        body = self._post_json(f"{base_url}/api/chat", payload, {})
        output_text = str((body.get("message") or {}).get("content") or "").strip()
        usage = {key: body.get(key) for key in ("prompt_eval_count", "eval_count", "total_duration")}
        return self._result("gemma", model, output_text, None, usage, started, external=False)

    def _read_meta(self, path: Path, raw: bytes, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("meta")
        if not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        model = self.model or os.getenv("AION_RECEIPT_META_MODEL") or get_ai_provider_model("meta") or "muse-spark-1.1"
        image_raw, mime = self._raster_image(path, raw)
        encoded = base64.b64encode(image_raw).decode("ascii")
        payload = {
            "model": model, "store": False, "max_output_tokens": 2500,
            "input": [{"role": "user", "content": [
                {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}", "detail": "high"},
                {"type": "input_text", "text": prompt},
            ]}],
            "text": {"format": {"type": "json_schema", "name": "finance_document_extraction", "strict": True, "schema": RECEIPT_SCHEMA}},
        }
        started = monotonic()
        body = self._post_json("https://api.meta.ai/v1/responses", payload, {"Authorization": f"Bearer {api_key}"})
        return self._result("meta", model, self._responses_output_text(body), body.get("id"), body.get("usage"), started, external=True)

    def _read_mistral(self, path: Path, raw: bytes, prompt: str) -> dict[str, Any]:
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_model, get_ai_provider_secret

        api_key = get_ai_provider_secret("mistral")
        if not api_key:
            raise RuntimeError("receipt_vision_provider_not_configured")
        model = self.model or os.getenv("AION_RECEIPT_MISTRAL_MODEL") or get_ai_provider_model("mistral") or "mistral-small-latest"
        image_raw, mime = self._raster_image(path, raw)
        encoded = base64.b64encode(image_raw).decode("ascii")
        schema_prompt = prompt + "\nReturn JSON only matching this schema:\n" + json.dumps(RECEIPT_SCHEMA, separators=(",", ":"))
        payload = {
            "model": model, "temperature": 0, "max_tokens": 2500,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": f"data:{mime};base64,{encoded}"},
                {"type": "text", "text": schema_prompt},
            ]}],
            "response_format": {"type": "json_object"},
        }
        started = monotonic()
        body = self._post_json("https://api.mistral.ai/v1/chat/completions", payload, {"Authorization": f"Bearer {api_key}"})
        choices = body.get("choices") or []
        output_text = str(((choices[0].get("message") or {}).get("content") or "") if choices else "").strip()
        return self._result("mistral", model, output_text, body.get("id"), body.get("usage"), started, external=True)

    def _provider_chain(self) -> list[str]:
        if self._client is not None:
            return ["openai"]
        selected = self.provider.strip().lower()
        aliases = {"anthropic": "claude", "xai": "grok", "moonshot": "kimi", "ollama": "gemma", "local_gemma": "gemma", "llama": "meta", "meta_ai": "meta", "mistralai": "mistral", "deep_seek": "deepseek"}
        selected = aliases.get(selected, selected)
        if selected != "auto":
            if selected not in {"openai", "gemini", "claude", "grok", "kimi", "gemma", "meta", "mistral", "deepseek"}:
                raise ValueError(f"receipt_vision_provider_unknown:{selected}")
            return [selected]
        from backend.modules.vault.ai_provider_key_store import get_ai_provider_public_record

        # Local vision models are deliberately opt-in: loading a multi-billion-parameter
        # model can pressure a desktop that is already running Tessaris and AION.
        requested = os.getenv("AION_RECEIPT_VISION_FALLBACK_ORDER", "gemini,claude,grok,kimi,mistral,meta,openai")
        chain = []
        for item in requested.split(","):
            provider = aliases.get(item.strip().lower(), item.strip().lower())
            if provider and provider not in chain and get_ai_provider_public_record(provider).get("connected"):
                chain.append(provider)
        if not chain:
            raise RuntimeError("receipt_vision_provider_not_configured")
        return chain

    @classmethod
    def provider_status(cls) -> list[dict[str, Any]]:
        from backend.modules.vault.ai_provider_key_store import list_ai_provider_public_records

        descriptions = {
            "openai": "OpenAI Responses vision + strict JSON schema", "gemini": "Gemini multimodal + response schema",
            "claude": "Claude vision + structured outputs", "grok": "Grok vision + structured outputs",
            "kimi": "Kimi multimodal + validated JSON", "gemma": "Local Ollama vision + JSON schema",
            "meta": "Meta Model API multimodal Responses + strict JSON schema",
            "mistral": "Mistral vision + validated JSON",
            "deepseek": "DeepSeek API; receipt vision awaits a verified image-input model",
        }
        records = []
        for item in list_ai_provider_public_records().get("providers", []):
            provider = item.get("id")
            if provider not in descriptions:
                continue
            records.append({
                "id": provider, "label": item.get("label"), "model": item.get("model"),
                "configured": bool(item.get("connected")) and provider != "deepseek",
                "status": ("no_verified_image_input" if provider == "deepseek" else ("ready" if item.get("connected") else item.get("reason"))),
                "transport": descriptions[provider], "local": provider == "gemma",
                "resource_warning": "High-memory local model; explicit selection only." if provider == "gemma" else None,
                "capability_checked_at_execution": True,
            })
        return records

    @staticmethod
    def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "Tessaris-Finance-Reader/1.0", **headers},
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"receipt_reader_http_{exc.code}") from exc

    @staticmethod
    def _responses_output_text(body: dict[str, Any]) -> str:
        return "".join(
            str(content.get("text") or "")
            for item in body.get("output", []) if item.get("type") == "message"
            for content in item.get("content", []) if content.get("type") == "output_text"
        ).strip()

    @staticmethod
    def _result(
        provider: str, model: str, output_text: str, response_id: Any, usage: Any,
        started: float, *, external: bool,
    ) -> dict[str, Any]:
        text = str(output_text or "").strip()
        if text.startswith("```"):
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        if not text:
            raise RuntimeError("receipt_vision_empty_response")
        return {
            "facts": json.loads(text), "provider": provider, "model": model,
            "response_id": response_id, "latency_ms": round((monotonic() - started) * 1000),
            "usage": usage or {}, "source_sent_externally": external,
            "provider_storage_requested": False,
        }

    @staticmethod
    def _raster_image(path: Path, raw: bytes) -> tuple[bytes, str]:
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png"}:
            return raw, mimetypes.guess_type(path.name)[0] or "image/jpeg"
        with tempfile.TemporaryDirectory(prefix="tessaris-receipt-raster-") as directory:
            converted = Path(directory) / "receipt.jpg"
            process = subprocess.run(
                ["/usr/bin/sips", "-s", "format", "jpeg", str(path), "--out", str(converted)],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if process.returncode != 0 or not converted.exists():
                raise RuntimeError("receipt_document_rasterisation_failed")
            return converted.read_bytes(), "image/jpeg"

    @staticmethod
    def _validated_facts(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("receipt_vision_schema_invalid")
        from jsonschema import Draft202012Validator

        errors = sorted(Draft202012Validator(RECEIPT_SCHEMA).iter_errors(value), key=lambda item: list(item.path))
        if errors:
            first = errors[0]
            location = ".".join(str(item) for item in first.path) or "root"
            raise ValueError(f"receipt_vision_schema_invalid:{location}:{first.message}")
        missing = [key for key in RECEIPT_SCHEMA["required"] if key not in value]
        if missing:
            raise ValueError("receipt_vision_schema_missing:" + ",".join(missing))
        if value.get("document_type") not in RECEIPT_SCHEMA["properties"]["document_type"]["enum"]:
            raise ValueError("receipt_vision_document_type_invalid")
        if not isinstance(value.get("line_items"), list) or not isinstance(value.get("category_signals"), list):
            raise ValueError("receipt_vision_schema_collection_invalid")
        if not isinstance(value.get("field_confidence"), dict) or not isinstance(value.get("uncertainties"), list):
            raise ValueError("receipt_vision_schema_metadata_invalid")
        for key, confidence in value["field_confidence"].items():
            try:
                value["field_confidence"][key] = min(1.0, max(0.0, float(confidence)))
            except (TypeError, ValueError) as exc:
                raise ValueError("receipt_vision_confidence_invalid") from exc
        try:
            value["primary_category_confidence"] = min(1.0, max(0.0, float(value.get("primary_category_confidence") or 0)))
        except (TypeError, ValueError) as exc:
            raise ValueError("receipt_vision_category_confidence_invalid") from exc
        return value
