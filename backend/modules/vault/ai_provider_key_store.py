from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[3]
STORE_PATH = ROOT / "data" / "local_vault" / "ai_provider_keys.json"

PROVIDERS: Dict[str, Dict[str, str]] = {
    "openai": {
        "label": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
    },
    "claude": {
        "label": "Claude / Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "alt_env_key": "CLAUDE_API_KEY",
        "model_env": "ANTHROPIC_MODEL",
        "default_model": "claude-sonnet-4-5",
    },
    "gemini": {
        "label": "Gemini / Google",
        "env_key": "GEMINI_API_KEY",
        "alt_env_key": "GOOGLE_API_KEY",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-2.5-flash",
    },
    "grok": {
        "label": "Grok / xAI",
        "env_key": "XAI_API_KEY",
        "alt_env_key": "GROK_API_KEY",
        "model_env": "GROK_MODEL",
        "default_model": "grok-4.5",
    },
    "kimi": {
        "label": "Kimi / Moonshot",
        "env_key": "MOONSHOT_API_KEY",
        "alt_env_key": "KIMI_API_KEY",
        "model_env": "KIMI_MODEL",
        "default_model": "kimi-k3",
    },
    "gemma": {
        "label": "Gemma / Ollama (local)",
        "env_key": "AION_LOCAL_GEMMA_TOKEN",
        "model_env": "AION_LOCAL_GEMMA_MODEL",
        "default_model": "gemma4:e2b",
    },
    "meta": {
        "label": "Meta AI",
        "env_key": "MODEL_API_KEY",
        "alt_env_key": "META_MODEL_API_KEY",
        "model_env": "META_MODEL_API_MODEL",
        "default_model": "muse-spark-1.1",
    },
    "mistral": {
        "label": "Mistral AI",
        "env_key": "MISTRAL_API_KEY",
        "model_env": "MISTRAL_MODEL",
        "default_model": "mistral-small-latest",
    },
    "deepseek": {
        "label": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "model_env": "DEEPSEEK_MODEL",
        "default_model": "deepseek-v4-pro",
    },
}


def normalize_provider_id(provider_id: str) -> str:
    value = str(provider_id or "").strip().lower()
    aliases = {
        "anthropic": "claude",
        "google": "gemini",
        "xai": "grok",
        "moonshot": "kimi",
        "local_gemma": "gemma",
        "ollama": "gemma",
        "llama": "meta",
        "meta_ai": "meta",
        "mistralai": "mistral",
        "deep_seek": "deepseek",
    }
    return aliases.get(value, value)


def _read_store() -> Dict[str, Any]:
    if not STORE_PATH.exists():
        return {"providers": {}}

    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"providers": {}}


def _write_store(data: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    try:
        os.chmod(STORE_PATH, 0o600)
    except Exception:
        pass


def mask_secret(value: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    if len(clean) <= 10:
        return "********"
    return f"{clean[:7]}…{clean[-4:]}"


def get_ai_provider_secret(provider_id: str) -> str:
    provider = normalize_provider_id(provider_id)
    data = _read_store()
    record = data.get("providers", {}).get(provider, {})

    vault_key = str(record.get("api_key") or "").strip()
    if vault_key:
        return vault_key

    meta = PROVIDERS.get(provider, {})
    for key_name in [meta.get("env_key"), meta.get("alt_env_key")]:
        if key_name and os.getenv(key_name, "").strip():
            return os.getenv(key_name, "").strip()

    return ""


def get_ai_provider_model(provider_id: str) -> str:
    provider = normalize_provider_id(provider_id)
    data = _read_store()
    record = data.get("providers", {}).get(provider, {})

    vault_model = str(record.get("model") or "").strip()
    if vault_model:
        return vault_model

    meta = PROVIDERS.get(provider, {})
    model_env = meta.get("model_env")
    if model_env and os.getenv(model_env, "").strip():
        return os.getenv(model_env, "").strip()

    return meta.get("default_model", "")


def get_ai_provider_public_record(provider_id: str) -> Dict[str, Any]:
    provider = normalize_provider_id(provider_id)
    meta = PROVIDERS.get(provider, {})

    data = _read_store()
    record = data.get("providers", {}).get(provider, {})

    vault_key = str(record.get("api_key") or "").strip()
    env_key = ""

    for key_name in [meta.get("env_key"), meta.get("alt_env_key")]:
        if key_name and os.getenv(key_name, "").strip():
            env_key = os.getenv(key_name, "").strip()
            break

    local_gemma = provider == "gemma" and _local_gemma_status().get("connected") is True
    connected = bool(vault_key or env_key or local_gemma)
    source = "local_ollama" if local_gemma else ("local_desktop_vault" if vault_key else ("env" if env_key else "missing"))

    receipt_vision = provider != "deepseek"
    return {
        "id": provider,
        "label": meta.get("label", provider),
        "connected": connected,
        "source": source,
        "masked_key": mask_secret(vault_key or env_key),
        "model": get_ai_provider_model(provider),
        "reason": None if connected else ("local_vision_model_unavailable" if provider == "gemma" else "missing_api_key"),
        "updated_at": record.get("updated_at"),
        "capabilities": {"boardroom": True, "receipt_vision": receipt_vision},
        "capability_note": (
            "Can serve as a Boardroom member and read receipts locally, but this model uses substantial Mac memory and should be selected explicitly."
            if provider == "gemma" else
            "Can serve as a Boardroom member and can read receipts when its selected model supports images."
            if receipt_vision else
            "Can serve as a Boardroom member; receipt reconciliation is disabled because the official API has no verified image-input route."
        ),
    }


def _local_gemma_status() -> Dict[str, Any]:
    import urllib.request

    base_url = os.getenv("AION_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("AION_LOCAL_GEMMA_MODEL", PROVIDERS["gemma"]["default_model"])
    request = urllib.request.Request(
        f"{base_url}/api/show", data=json.dumps({"model": model}).encode("utf-8"),
        method="POST", headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=0.5) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception:
        return {"connected": False, "model": model, "capabilities": []}
    capabilities = body.get("capabilities") or []
    return {"connected": "vision" in capabilities, "model": model, "capabilities": capabilities}


def list_ai_provider_public_records() -> Dict[str, Any]:
    records = [get_ai_provider_public_record(provider) for provider in PROVIDERS.keys()]
    return {
        "schema_version": "aion.vault_ai_providers.v1",
        "storage": "local_desktop_vault_or_env_fallback",
        "store_path": str(STORE_PATH),
        "providers": records,
        "connected_count": sum(1 for item in records if item.get("connected")),
        "note": "API keys are never returned raw. This local desktop vault should later be backed by OS keychain/encrypted storage.",
    }


def set_ai_provider_key(provider_id: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
    provider = normalize_provider_id(provider_id)
    if provider not in PROVIDERS:
        raise ValueError(f"unknown_provider:{provider_id}")

    clean_key = str(api_key or "").strip()
    if not clean_key:
        raise ValueError("empty_api_key")

    data = _read_store()
    providers = data.setdefault("providers", {})
    providers[provider] = {
        "api_key": clean_key,
        "model": str(model or "").strip(),
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "source": "local_desktop_vault",
    }
    _write_store(data)
    return get_ai_provider_public_record(provider)


def delete_ai_provider_key(provider_id: str) -> Dict[str, Any]:
    provider = normalize_provider_id(provider_id)
    data = _read_store()
    providers = data.setdefault("providers", {})
    providers.pop(provider, None)
    _write_store(data)
    return get_ai_provider_public_record(provider)
