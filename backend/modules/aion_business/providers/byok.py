from __future__ import annotations

import os
from typing import Dict, Optional

from pydantic import BaseModel, Field


class BYOKStatus(BaseModel):
    provider: str
    configured: bool
    source: Optional[str] = None
    key_present: bool = False
    metadata: Dict[str, str] = Field(default_factory=dict)


class BYOKManager:
    """
    Minimal bring-your-own-key manager for provider-backed runtime services.

    v1 behavior:
    - resolve provider API keys from environment
    - report whether a provider is configured
    - avoid returning raw secrets
    """

    ENV_MAP = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "resend": "RESEND_API_KEY",
    }

    def get_api_key(self, provider: str) -> Optional[str]:
        env_name = self.ENV_MAP.get(provider)
        if not env_name:
            return None
        value = os.getenv(env_name)
        if not value or not value.strip():
            return None
        return value.strip()

    def is_configured(self, provider: str) -> bool:
        return self.get_api_key(provider) is not None

    def status(self, provider: str) -> BYOKStatus:
        env_name = self.ENV_MAP.get(provider)
        key = self.get_api_key(provider)

        if not env_name:
            return BYOKStatus(
                provider=provider,
                configured=False,
                source=None,
                key_present=False,
                metadata={"reason": "unknown_provider"},
            )

        return BYOKStatus(
            provider=provider,
            configured=key is not None,
            source=env_name,
            key_present=key is not None,
            metadata={},
        )

    def all_statuses(self) -> Dict[str, BYOKStatus]:
        return {
            provider: self.status(provider)
            for provider in sorted(self.ENV_MAP.keys())
        }