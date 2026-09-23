"""Known local-model chat profiles used by the Tessaris Vault.

Raw GGUF weights are not necessarily ready for a conversation runtime.  A model
must either arrive in an upstream Ollama package (which carries its own template)
or have a reviewed Tessaris profile before it may be offered as a chat model.
"""

from __future__ import annotations

from typing import Any


def profile_for(model_id: str) -> dict[str, Any]:
    """Return a public, non-secret runtime profile for a Vault model card."""
    normalized = str(model_id or "").casefold()
    if "gpt-oss" in normalized:
        return {
            "status": "profile_ready",
            "engine": "ollama",
            "conversation_format": "openai_harmony",
            "template_source": "official Ollama gpt-oss package template",
            "raw_gguf_policy": "create a Tessaris chat alias with the reviewed Harmony template before use",
            "reasoning_display": "disabled for concise business-chat replies",
        }
    if "gemma" in normalized:
        return {
            "status": "package_managed",
            "engine": "ollama",
            "conversation_format": "upstream_package",
            "raw_gguf_policy": "do not infer a template; use the upstream Ollama package or a reviewed package card",
        }
    if "qwen" in normalized:
        if normalized == "qwen3-8b-fast-local-q4":
            return {
                "status": "owner_approved_bounded", "engine": "llama.cpp",
                "adapter": "openai_compatible_bounded_chat.v1",
                "conversation_format": "verified_qwen3_chat_template",
                "endpoint": "http://127.0.0.1:8897",
                "chat_template_kwargs": {"enable_thinking": False},
                "max_output_tokens": 320,
                "context_size": 4096,
                "parallel_slots": 1,
                "raw_gguf_policy": "exact hash and bounded warehouse manifest required",
                "finance_arithmetic": "verified_tessaris_tools_required",
                "network_fallback": False, "tool_execution": False,
            }
        return {
            "status": "package_card_required",
            "engine": "ollama",
            "conversation_format": "requires_verified_upstream_template",
            "raw_gguf_policy": "keep unavailable until its exact Qwen release and template are verified",
        }
    if "mistral" in normalized or "ministral" in normalized or "deepseek" in normalized or "granite" in normalized:
        return {
            "status": "package_card_required",
            "engine": "ollama",
            "conversation_format": "requires_verified_upstream_template",
            "raw_gguf_policy": "keep unavailable until a signed Tessaris package card provides the exact template",
        }
    return {
        "status": "quarantined_until_profiled",
        "engine": "undetermined",
        "conversation_format": "unknown",
        "raw_gguf_policy": "do not activate a raw model until a reviewed profile is attached",
    }
