# backend/modules/aion_business/providers/router.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from backend.modules.aion_business.providers.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicAdapterResult,
)
from backend.modules.aion_business.providers.byok import BYOKManager
from backend.modules.aion_business.providers.capability_manifest import provider_manifest_for_ui
from backend.modules.aion_business.providers.local_adapter import (
    LocalAdapter,
    LocalAdapterResult,
)
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
    LocalAdapterResult,
]


class ProviderRouter:
    def __init__(
        self,
        *,
        openai_adapter: Optional[OpenAIAdapter] = None,
        anthropic_adapter: Optional[AnthropicAdapter] = None,
        resend_adapter: Optional[ResendAdapter] = None,
        local_adapter: Optional[LocalAdapter] = None,
        byok_manager: Optional[BYOKManager] = None,
    ):
        self.openai_adapter = openai_adapter or OpenAIAdapter()
        self.anthropic_adapter = anthropic_adapter or AnthropicAdapter()
        self.resend_adapter = resend_adapter or ResendAdapter()
        self.local_adapter = local_adapter or LocalAdapter()
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
                raw=ProviderRouter._build_blocked_raw(
                    provider=preferred_provider or resolved_policy.default_provider,
                    model=preferred_model or "",
                    metadata={**metadata, "capability": capability},
                    capability=capability,
                    error_code=f"role_not_allowed_by_policy:{role_type}",
                ),
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
                raw=ProviderRouter._build_blocked_raw(
                    provider=preferred_provider or resolved_policy.default_provider,
                    model=preferred_model or "",
                    metadata={**metadata, "capability": capability},
                    capability=capability,
                    error_code=f"capability_not_allowed_by_policy:{capability}",
                ),
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
                raw=ProviderRouter._build_blocked_raw(
                    provider=preferred_provider or resolved_policy.default_provider,
                    model=preferred_model or "",
                    metadata={**metadata, "capability": capability},
                    capability=capability,
                    error_code=f"skill_blocked_by_policy:{skill_id}",
                ),
            )

        primary_provider = preferred_provider or resolved_policy.default_provider
        provider_chain = self._build_provider_chain(
            primary_provider=primary_provider,
            fallback_provider=resolved_policy.fallback_provider,
            metadata=metadata,
        )

        first_error_result: Optional[ProviderAdapterResult] = None

        for index, provider_name in enumerate(provider_chain):
            if capability and not self._provider_supports_capability(provider_name, capability):
                if first_error_result is None:
                    first_error_result = OpenAIAdapterResult(
                        ok=False,
                        provider=provider_name,
                        model=preferred_model or "",
                        content="",
                        usage={},
                        latency_ms=0,
                        error_code=f"provider_capability_not_supported:{provider_name}:{capability}",
                        raw={"metadata": {**metadata, "capability": capability}, "capability_manifest_checked": True},
                    )
                continue

            result = self._call_provider(
                provider=provider_name,
                prompt=prompt,
                system_prompt=system_prompt,
                policy=resolved_policy,
                preferred_model=preferred_model if provider_name == primary_provider else None,
                metadata={**metadata, "capability": capability},
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

    def capability_manifest(self) -> Dict[str, Any]:
        return provider_manifest_for_ui(
            provider_status={
                "local": True,
                "openai": self.byok_manager.is_configured("openai"),
                "anthropic": self.byok_manager.is_configured("anthropic"),
                "resend": self.byok_manager.is_configured("resend"),
            }
        )

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

    def _provider_supports_capability(self, provider: str, capability: str) -> bool:
        manifest = self.capability_manifest()
        providers = manifest.get("providers", {})
        provider_info = providers.get(str(provider or "").strip().lower(), {})

        if not isinstance(provider_info, dict):
            return False

        capabilities = provider_info.get("capabilities", [])
        if capabilities == "*":
            return True

        if isinstance(capabilities, list) and capability in capabilities:
            return True

        aliases = {
            "drafting": "draft",
            "summarization": "summarize",
            "classification": "classify",
            "planning": "plan",
            "reasoning": "reason",
            "analysis": "analyze",
            "rewrite": "rewrite",
        }

        alias = aliases.get(str(capability or "").strip().lower())
        return isinstance(capabilities, list) and alias in capabilities

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
            return self.local_adapter.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                capability=str(metadata.get("capability") or metadata.get("requested_capability") or "drafting"),
                metadata=metadata,
                preferred_model=preferred_model,
                max_tokens=max_tokens,
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
            raw=ProviderRouter._raw_with_provider_audit(
                raw=result.raw or {},
                result=result,
                fallback_used=fallback_used,
            ),
        )


    @staticmethod
    def _raw_with_provider_audit(
        *,
        raw: Dict[str, Any] | None,
        result: ProviderAdapterResult,
        fallback_used: bool,
    ) -> Dict[str, Any]:
        enriched = dict(raw or {})
        enriched["provider_audit"] = ProviderRouter._build_provider_audit(
            result=result,
            fallback_used=fallback_used,
        )
        return enriched

    @staticmethod
    def _build_provider_audit(
        *,
        result: ProviderAdapterResult,
        fallback_used: bool,
    ) -> Dict[str, Any]:
        raw = dict(result.raw or {})
        metadata = dict(raw.get("metadata") or {})
        usage = dict(result.usage or {})

        capability = str(
            metadata.get("capability")
            or metadata.get("requested_capability")
            or raw.get("capability")
            or usage.get("capability")
            or ""
        )

        def as_int(value: Any, default: int = 0) -> int:
            try:
                if value is None:
                    return default
                return int(value)
            except (TypeError, ValueError):
                return default

        def as_float(value: Any, default: float = 0.0) -> float:
            try:
                if value is None:
                    return default
                return float(value)
            except (TypeError, ValueError):
                return default

        prompt_tokens = as_int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or raw.get("prompt_tokens")
            or raw.get("input_tokens")
        )
        completion_tokens = as_int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or raw.get("completion_tokens")
            or raw.get("output_tokens")
        )
        total_tokens = as_int(
            usage.get("total_tokens")
            or raw.get("total_tokens")
            or (prompt_tokens + completion_tokens)
        )

        token_count = total_tokens
        if token_count <= 0:
            token_count = as_int(usage.get("max_tokens_requested") or metadata.get("max_tokens_requested"))

        cost_estimate = as_float(
            usage.get("cost_estimate")
            or raw.get("cost_estimate")
            or metadata.get("cost_estimate")
        )

        error_code = result.error_code
        degradation_event = "none"
        if error_code:
            degradation_event = str(error_code)
        elif fallback_used:
            degradation_event = "provider_fallback_used"

        provider = str(result.provider or usage.get("provider") or "unknown")
        is_local = provider == "local" or bool(usage.get("local_only"))

        external_writes = str(
            usage.get("external_writes")
            or raw.get("external_writes")
            or metadata.get("external_writes")
            or ("blocked" if is_local else "approval_required")
        )

        business_state_mutation = str(
            metadata.get("business_state_mutation")
            or raw.get("business_state_mutation")
            or "human_review_guarded"
        )

        return {
            "trace_type": "provider_audit",
            "provider": provider,
            "model": str(result.model or usage.get("model") or ""),
            "capability": capability,
            "policy_checked": True,
            "fallback_used": bool(fallback_used),
            "latency_ms": as_int(result.latency_ms),
            "runtime_duration_ms": as_int(result.latency_ms),
            "token_count": as_int(token_count),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_estimate": cost_estimate,
            "degradation_mode": str(
                raw.get("degradation_mode")
                or metadata.get("degradation_mode")
                or ("fail_closed" if error_code else "normal")
            ),
            "degradation_event": degradation_event,
            "external_writes": external_writes,
            "business_state_mutation": business_state_mutation,
            "legacy_business_state_mutation": "blocked" if provider == "local" else business_state_mutation,
            "local_only": bool(usage.get("local_only") is True or provider == "local"),
            "would_grant_permission": False,
            "failed_closed": bool(error_code and not fallback_used),
            "error_code": error_code,
            "capability_manifest_checked": bool(raw.get("capability_manifest_checked")),
            "safe_local_adapter": bool(raw.get("safe_local_adapter")),
        }

    @staticmethod
    def _build_blocked_raw(
        *,
        provider: str,
        model: str,
        metadata: Dict[str, Any],
        capability: str,
        error_code: str,
    ) -> Dict[str, Any]:
        blocked = OpenAIAdapterResult(
            ok=False,
            provider=provider,
            model=model,
            content="",
            usage={},
            latency_ms=0,
            error_code=error_code,
            raw={
                "metadata": {**dict(metadata or {}), "capability": capability},
                "capability_manifest_checked": True,
            },
        )
        return ProviderRouter._raw_with_provider_audit(
            raw=blocked.raw or {},
            result=blocked,
            fallback_used=False,
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