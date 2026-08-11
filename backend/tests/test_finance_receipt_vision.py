from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.finance_receipt_vision import FinanceReceiptVisionReader


def _facts() -> dict:
    return {
        "document_type": "receipt", "supplier": "Test Merchant", "document_date": "2026-08-09",
        "currency": "EUR", "total": 12.1, "net": 10.0, "tax": 2.1, "tip": None,
        "invoice_number": None, "due_date": None, "description": "Materials",
        "payment_method": "card", "card_last_four": "1234", "merchant_tax_id": None,
        "merchant_address": None,
        "line_items": [{"description": "Screws", "quantity": 1, "unit_price": 10, "total": 10, "tax_rate": 21}],
        "category_signals": ["materials"], "primary_category": "materials",
        "primary_category_confidence": 0.9,
        "field_confidence": {
            "supplier": 1, "document_date": 1, "currency": 1, "total": 1, "net": 1,
            "tax": 1, "invoice_number": 0, "description": 0.9, "payment_method": 0.9,
            "line_items": 0.8,
        },
        "uncertainties": [],
    }


class CapturingReader(FinanceReceiptVisionReader):
    def __init__(self, provider: str, response: dict) -> None:
        super().__init__(provider=provider)
        self.response = response
        self.calls: list[tuple[str, dict, dict]] = []

    def _post_json(self, url: str, payload: dict, headers: dict) -> dict:
        self.calls.append((url, payload, headers))
        if self.provider == "gemma" and url.endswith("/api/show"):
            return {"capabilities": ["completion", "vision"]}
        return self.response


@pytest.fixture
def image(tmp_path):
    path = tmp_path / "receipt.png"
    path.write_bytes(b"not-decoded-by-mocked-transport")
    return path


@pytest.fixture(autouse=True)
def provider_credentials(monkeypatch):
    monkeypatch.setattr("backend.modules.vault.ai_provider_key_store.get_ai_provider_secret", lambda provider: "test-key")
    monkeypatch.setattr("backend.modules.vault.ai_provider_key_store.get_ai_provider_model", lambda provider: {
        "claude": "claude-test", "grok": "grok-test", "kimi": "kimi-test", "gemma": "gemma-test",
        "meta": "meta-test", "mistral": "mistral-test", "deepseek": "deepseek-test",
    }.get(provider, "test-model"))


def test_claude_uses_image_and_structured_output(image) -> None:
    reader = CapturingReader("claude", {"id": "msg_1", "stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(_facts())}]})
    result = reader.read(image)
    url, payload, headers = reader.calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert payload["messages"][0]["content"][0]["type"] == "image"
    assert payload["output_config"]["format"]["type"] == "json_schema"
    assert headers["x-api-key"] == "test-key"
    assert result["provider"] == "claude"


def test_grok_uses_responses_vision_without_storage(image) -> None:
    body = {"id": "resp_1", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_facts())}]}]}
    reader = CapturingReader("grok", body)
    result = reader.read(image)
    url, payload, _ = reader.calls[0]
    assert url == "https://api.x.ai/v1/responses"
    assert payload["store"] is False
    assert payload["input"][0]["content"][0]["type"] == "input_image"
    assert payload["text"]["format"]["type"] == "json_schema"
    assert result["provider"] == "grok"


def test_kimi_uses_openai_compatible_multimodal_message(image) -> None:
    reader = CapturingReader("kimi", {"id": "chat_1", "choices": [{"message": {"content": json.dumps(_facts())}}]})
    result = reader.read(image)
    url, payload, _ = reader.calls[0]
    assert url == "https://api.moonshot.ai/v1/chat/completions"
    assert payload["messages"][0]["content"][0]["type"] == "image_url"
    assert payload["response_format"] == {"type": "json_object"}
    assert result["provider"] == "kimi"


def test_local_gemma_requires_vision_and_stays_on_device(image) -> None:
    reader = CapturingReader("gemma", {"message": {"content": json.dumps(_facts())}, "eval_count": 20})
    result = reader.read(image)
    assert reader.calls[0][0].endswith("/api/show")
    assert reader.calls[1][0].endswith("/api/chat")
    assert reader.calls[1][1]["format"]["type"] == "object"
    assert result["source_sent_externally"] is False


def test_meta_uses_multimodal_responses_and_strict_schema(image) -> None:
    body = {"id": "meta_1", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_facts())}]}]}
    reader = CapturingReader("meta", body)
    result = reader.read(image)
    url, payload, _ = reader.calls[0]
    assert url == "https://api.meta.ai/v1/responses"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert result["provider"] == "meta"


def test_mistral_uses_vision_chat_and_validated_json(image) -> None:
    reader = CapturingReader("mistral", {"id": "mistral_1", "choices": [{"message": {"content": json.dumps(_facts())}}]})
    result = reader.read(image)
    url, payload, _ = reader.calls[0]
    assert url == "https://api.mistral.ai/v1/chat/completions"
    assert payload["messages"][0]["content"][0]["type"] == "image_url"
    assert payload["response_format"] == {"type": "json_object"}
    assert result["provider"] == "mistral"


def test_deepseek_fails_closed_for_receipts_without_verified_vision(image) -> None:
    with pytest.raises(RuntimeError, match="no_verified_image_input"):
        FinanceReceiptVisionReader(provider="deepseek").read(image)


def test_provider_output_must_satisfy_the_same_contract(image) -> None:
    reader = CapturingReader("kimi", {"choices": [{"message": {"content": '{"supplier":"Incomplete"}'}}]})
    with pytest.raises(ValueError, match="receipt_vision_schema_invalid"):
        reader.read(image)


def test_explicit_provider_does_not_silently_fallback() -> None:
    assert FinanceReceiptVisionReader(provider="anthropic")._provider_chain() == ["claude"]
    assert FinanceReceiptVisionReader(provider="local_gemma")._provider_chain() == ["gemma"]
    assert FinanceReceiptVisionReader(provider="llama")._provider_chain() == ["meta"]
    assert FinanceReceiptVisionReader(provider="mistralai")._provider_chain() == ["mistral"]
