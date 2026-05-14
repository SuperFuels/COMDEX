# backend/modules/aion_business/providers/router.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from backend.modules.aion_business.providers.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicAdapterResult,
)
from backend.modules.aion_business.providers.byok import BYOKManager
from backend.modules.aion_business.providers.contracts import (
    ProviderRequest,
    ProviderResult,
)
from backend.modules.aion_business.providers.model_policy import (
    ModelPolicy,
    default_anthropic_reasoning_policy,
    default_openai_copy_policy,
)
from backend.modules.aion_business.providers.openai_adapter import (
    OpenAIAdapter,
    OpenAIAdapterResult,
)
from backend.modules.aion_business.providers.resend_adapter import (
    ResendAdapter,
    ResendAdapterResult,
)


@dataclass(slots=True)
class ProviderRouterResult:
    ok: bool
    provider: str
    model: str
    content: str
    usage: Dict[str, Any]
    latency_ms: int
    policy_id: str
    fallback_used: bool = False
    error_code: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


ProviderAdapterResult = Union[
    OpenAIAdapterResult,
    AnthropicAdapterResult,
    ResendAdapterResult,
]


class ProviderRouter:
    def __init__(
        self,
        *,
        openai_adapter: Optional[OpenAIAdapter] = None,
        anthropic_adapter: Optional[AnthropicAdapter] = None,
        resend_adapter: Optional[ResendAdapter] = None,
        byok_manager: Optional[BYOKManager] = None,
    ):
        self.openai_adapter = openai_adapter or OpenAIAdapter()
        self.anthropic_adapter = anthropic_adapter or AnthropicAdapter()
        self.resend_adapter = resend_adapter or ResendAdapter()
        self.byok_manager = byok_manager or BYOKManager()

    def generate(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str] = None,
        policy: Optional[ModelPolicy] = None,
        policy_ref: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        capability: str = "drafting",
        role_type: Optional[str] = None,
        skill_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_tokens: int = 512,
    ) -> ProviderRouterResult:
        resolved_policy = policy or self.resolve_policy(policy_ref)
        metadata = dict(metadata or {})

        if role_type and not resolved_policy.allows_role(role_type):
            return ProviderRouterResult(
                ok=False,
                provider=preferred_provider or resolved_policy.default_provider,
                model=preferred_model or "",
                content="",
                usage={},
                latency_ms=0,
                policy_id=resolved_policy.id,
                fallback_used=False,
                error_code=f"role_not_allowed_by_policy:{role_type}",
                raw={"metadata": metadata},
            )

        if capability and not resolved_policy.allows_capability(capability):
            return ProviderRouterResult(
                ok=False,
                provider=preferred_provider or resolved_policy.default_provider,
                model=preferred_model or "",
                content="",
                usage={},
                latency_ms=0,
                policy_id=resolved_policy.id,
                fallback_used=False,
                error_code=f"capability_not_allowed_by_policy:{capability}",
                raw={"metadata": metadata},
            )

        if skill_id and resolved_policy.blocks_skill(skill_id):
            return ProviderRouterResult(
                ok=False,
                provider=preferred_provider or resolved_policy.default_provider,
                model=preferred_model or "",
                content="",
                usage={},
                latency_ms=0,
                policy_id=resolved_policy.id,
                fallback_used=False,
                error_code=f"skill_blocked_by_policy:{skill_id}",
                raw={"metadata": metadata},
            )

        primary_provider = preferred_provider or resolved_policy.default_provider
        provider_chain = self._build_provider_chain(
            primary_provider=primary_provider,
            fallback_provider=resolved_policy.fallback_provider,
            metadata=metadata,
        )

        first_error_result: Optional[ProviderAdapterResult] = None

        for index, provider_name in enumerate(provider_chain):
            result = self._call_provider(
                provider=provider_name,
                prompt=prompt,
                system_prompt=system_prompt,
                policy=resolved_policy,
                preferred_model=preferred_model if provider_name == primary_provider else None,
                metadata=metadata,
                max_tokens=max_tokens,
            )

            if result.ok and str(result.content or "").strip():
                return self._normalize_result(
                    result=result,
                    policy_id=resolved_policy.id,
                    fallback_used=index > 0,
                )

            if first_error_result is None:
                first_error_result = result

        return self._normalize_result(
            result=first_error_result
            or OpenAIAdapterResult(
                ok=False,
                provider=primary_provider or "openai",
                model=preferred_model or "",
                content="",
                usage={},
                latency_ms=0,
                error_code="provider_generation_failed",
                raw={"metadata": metadata},
            ),
            policy_id=resolved_policy.id,
            fallback_used=False,
        )

    def generate_from_request(
        self,
        request: ProviderRequest,
        *,
        policy: Optional[ModelPolicy] = None,
        policy_ref: Optional[str] = None,
    ) -> ProviderResult:
        router_result = self.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            policy=policy,
            policy_ref=policy_ref or request.policy_id,
            preferred_provider=request.provider,
            preferred_model=request.model,
            capability=request.capability,
            role_type=request.role_type,
            skill_id=request.skill_id,
            metadata=request.metadata,
            max_tokens=request.max_tokens,
        )
        return self._to_provider_result(router_result)

    def resolve_policy(self, policy_ref: Optional[str]) -> ModelPolicy:
        if policy_ref == "anthropic_reasoning":
            return default_anthropic_reasoning_policy()
        return default_openai_copy_policy()

    def _build_provider_chain(
        self,
        *,
        primary_provider: Optional[str],
        fallback_provider: Optional[str],
        metadata: Dict[str, Any],
    ) -> list[str]:
        chain: list[str] = []

        def add_provider(value: Optional[str]) -> None:
            if isinstance(value, str) and value.strip():
                normalized = value.strip().lower()
                if normalized not in chain:
                    chain.append(normalized)

        add_provider(primary_provider)
        add_provider(fallback_provider)

        for key in (
            "fallback_provider",
            "workspace_fallback_provider",
            "user_fallback_provider",
            "selected_provider",
            "preferred_provider",
            "workspace_provider",
            "default_provider",
        ):
            add_provider(metadata.get(key))

        add_provider("local")
        add_provider("openai")
        add_provider("anthropic")

        return chain

    def _call_provider(
        self,
        *,
        provider: str,
        prompt: str,
        system_prompt: Optional[str],
        policy: ModelPolicy,
        preferred_model: Optional[str],
        metadata: Optional[Dict[str, Any]],
        max_tokens: int,
    ) -> ProviderAdapterResult:
        metadata = dict(metadata or {})
        normalized_provider = str(provider or "").strip().lower()

        if normalized_provider == "local":
            return OpenAIAdapterResult(
                ok=False,
                provider="local",
                model=preferred_model or "gemma",
                content="",
                usage={},
                latency_ms=0,
                error_code="local_provider_not_implemented",
                raw={"metadata": metadata},
            )

        if not self.byok_manager.is_configured(normalized_provider):
            if normalized_provider == "anthropic":
                return AnthropicAdapterResult(
                    ok=False,
                    provider="anthropic",
                    model=preferred_model or self.anthropic_adapter.model,
                    content="",
                    usage={},
                    latency_ms=0,
                    error_code="missing_anthropic_api_key",
                    raw={"metadata": metadata},
                )

            if normalized_provider == "resend":
                return ResendAdapterResult(
                    ok=False,
                    provider="resend",
                    model=preferred_model or self.resend_adapter.model,
                    content="",
                    usage={},
                    latency_ms=0,
                    error_code="missing_resend_api_key",
                    raw={"metadata": metadata},
                )

            return OpenAIAdapterResult(
                ok=False,
                provider="openai",
                model=preferred_model or self.openai_adapter.model,
                content="",
                usage={},
                latency_ms=0,
                error_code="missing_openai_api_key",
                raw={"metadata": metadata},
            )

        if normalized_provider == "anthropic":
            return self.anthropic_adapter.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                policy=policy,
                metadata=metadata,
                preferred_model=preferred_model,
                max_tokens=max_tokens,
            )

        if normalized_provider == "resend":
            return self.resend_adapter.send_email(
                prompt=prompt,
                system_prompt=system_prompt,
                policy=policy,
                metadata=metadata,
                preferred_model=preferred_model,
                max_tokens=max_tokens,
            )

        return self.openai_adapter.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            policy=policy,
            metadata=metadata,
            preferred_model=preferred_model,
        )

    @staticmethod
    def _normalize_result(
        *,
        result: ProviderAdapterResult,
        policy_id: str,
        fallback_used: bool,
    ) -> ProviderRouterResult:
        return ProviderRouterResult(
            ok=result.ok,
            provider=result.provider,
            model=result.model,
            content=result.content,
            usage=dict(result.usage or {}),
            latency_ms=result.latency_ms,
            policy_id=policy_id,
            fallback_used=fallback_used,
            error_code=result.error_code,
            raw=result.raw,
        )

    @staticmethod
    def _to_provider_result(router_result: ProviderRouterResult) -> ProviderResult:
        warnings = []
        if router_result.error_code:
            warnings.append(router_result.error_code)

        return ProviderResult(
            ok=router_result.ok,
            provider=router_result.provider,
            model=router_result.model,
            content=router_result.content,
            usage=dict(router_result.usage or {}),
            latency_ms=router_result.latency_ms,
            fallback_used=router_result.fallback_used,
            error_code=router_result.error_code,
            raw=router_result.raw,
            policy_id=router_result.policy_id,
            warnings=warnings,
        )