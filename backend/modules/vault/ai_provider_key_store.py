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
        "default_model": "claude-3-5-sonnet-20241022",
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
        "default_model": "grok-beta",
    },
}


def normalize_provider_id(provider_id: str) -> str:
    value = str(provider_id or "").strip().lower()
    aliases = {
        "anthropic": "claude",
        "google": "gemini",
        "xai": "grok",
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

    connected = bool(vault_key or env_key)
    source = "local_desktop_vault" if vault_key else ("env" if env_key else "missing")

    return {
        "id": provider,
        "label": meta.get("label", provider),
        "connected": connected,
        "source": source,
        "masked_key": mask_secret(vault_key or env_key),
        "model": get_ai_provider_model(provider),
        "reason": None if connected else "missing_api_key",
        "updated_at": record.get("updated_at"),
    }


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
