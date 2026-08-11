# backend/modules/aion_business/skills/draft_content.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult
from backend.modules.aion_business.providers.contracts import ProviderRequest
from backend.modules.aion_business.providers.model_policy import (
    ModelPolicy,
    default_anthropic_reasoning_policy,
    default_openai_copy_policy,
)
from backend.modules.aion_business.providers.router import ProviderRouter
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.skills.base import (
    BaseSkill,
    SkillValidationError,
)


DEFAULT_LOCAL_PROVIDER = "local"
DEFAULT_LOCAL_MODEL = "gemma"
DEFAULT_COPY_POLICY_REF = "copy_default"


class DraftContentSkill(BaseSkill):
    """
    Provider-routed content drafting skill.

    Routing order:
    1. explicit request provider/model
    2. metadata-selected provider/model
    3. local default provider/model
    4. fallback content must be usable publish-ready content
    """

    def __init__(
        self,
        *,
        provider_router: Optional[ProviderRouter] = None,
        audit_log: Optional[AuditLog] = None,
    ):
        self.provider_router = provider_router or ProviderRouter()
        self.audit_log = audit_log or AuditLog()

    @property
    def skill_id(self) -> str:
        return "draft_content"

    def validate_request(self, request: SkillRunRequest) -> None:
        super().validate_request(request)

        prompt = request.input_payload.get("prompt")
        if not prompt or not isinstance(prompt, str):
            raise SkillValidationError("missing_prompt")

        system_prompt = request.input_payload.get("system_prompt")
        if system_prompt is not None and not isinstance(system_prompt, str):
            raise SkillValidationError("system_prompt_must_be_string")

        provider = request.input_payload.get("provider")
        if provider is not None and not isinstance(provider, str):
            raise SkillValidationError("provider_must_be_string")

        preferred_model = request.input_payload.get("preferred_model")
        if preferred_model is not None and not isinstance(preferred_model, str):
            raise SkillValidationError("preferred_model_must_be_string")

        title = request.input_payload.get("title")
        if title is not None and not isinstance(title, str):
            raise SkillValidationError("title_must_be_string")

        metadata = request.input_payload.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise SkillValidationError("metadata_must_be_object")

        role_type = request.input_payload.get("role_type")
        if role_type is not None and not isinstance(role_type, str):
            raise SkillValidationError("role_type_must_be_string")

        capability = request.input_payload.get("capability")
        if capability is not None and not isinstance(capability, str):
            raise SkillValidationError("capability_must_be_string")

        max_tokens = request.input_payload.get("max_tokens")
        if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
            raise SkillValidationError("invalid_max_tokens")

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        prompt = str(request.input_payload["prompt"])
        system_prompt = request.input_payload.get("system_prompt")
        title = request.input_payload.get("title")
        metadata = dict(request.input_payload.get("metadata", {}))
        capability = str(request.input_payload.get("capability", "drafting"))
        role_type = request.input_payload.get("role_type")
        max_tokens = int(request.input_payload.get("max_tokens", 512))

        provider = self._resolve_provider(request, metadata)
        preferred_model = self._resolve_model(request, metadata, provider)
        policy = self._resolve_policy(
            request,
            provider=provider,
            preferred_model=preferred_model,
        )
        policy_ref = (
            request.input_payload.get("model_policy_ref")
            or metadata.get("model_policy_ref")
            or policy.id
            or DEFAULT_COPY_POLICY_REF
        )

        provider_request = ProviderRequest(
            provider=provider,
            model=preferred_model,
            prompt=prompt,
            system_prompt=system_prompt,
            capability=capability,
            role_type=role_type,
            skill_id=self.skill_id,
            policy_id=policy_ref,
            metadata=metadata,
            max_tokens=max_tokens,
        )

        provider_result = self.provider_router.generate_from_request(
            provider_request,
            policy=policy,
            policy_ref=policy_ref,
        )

        self._maybe_audit_provider_call(
            request=request,
            provider_request=provider_request,
            provider_result=provider_result,
        )

        warnings = list(provider_result.warnings)

        if provider_result.ok and str(provider_result.content or "").strip():
            drafted_text = str(provider_result.content).strip()
            fallback_used = bool(provider_result.fallback_used)
        else:
            drafted_text = self._build_fallback_content(
                prompt=prompt,
                title=title,
                metadata=metadata,
                request=request,
            )
            if provider_result.error_code and provider_result.error_code not in warnings:
                warnings.append(provider_result.error_code)
            fallback_used = True

        output_payload = {
            "title": title,
            "draft": drafted_text,
            "provider": provider_result.provider or provider,
            "model": provider_result.model or preferred_model,
            "usage": dict(provider_result.usage or {}),
            "fallback_used": fallback_used,
            "policy_id": provider_result.policy_id or policy_ref,
        }

        return SkillRunResult(
            ok=True,
            skill_id=self.skill_id,
            output_payload=output_payload,
            artifacts=[],
            warnings=warnings,
            error_code=None,
            trace={
                "provider_requested": provider,
                "provider_used": provider_result.provider or provider,
                "model_requested": preferred_model,
                "model_used": provider_result.model or preferred_model,
                "fallback_used": fallback_used,
                "policy_id": provider_result.policy_id or policy_ref,
            },
            side_effects_applied=False,
        )

    def _resolve_provider(
        self,
        request: SkillRunRequest,
        metadata: Dict[str, Any],
    ) -> str:
        explicit_provider = request.input_payload.get("provider")
        if isinstance(explicit_provider, str) and explicit_provider.strip():
            return explicit_provider.strip()

        for key in (
            "preferred_provider",
            "selected_provider",
            "user_selected_provider",
            "workspace_provider",
            "default_provider",
        ):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return DEFAULT_LOCAL_PROVIDER

    def _resolve_model(
        self,
        request: SkillRunRequest,
        metadata: Dict[str, Any],
        provider: str,
    ) -> Optional[str]:
        explicit_model = request.input_payload.get("preferred_model")
        if isinstance(explicit_model, str) and explicit_model.strip():
            return explicit_model.strip()

        for key in (
            "preferred_model",
            "selected_model",
            "user_selected_model",
            "workspace_model",
            "default_model",
        ):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if provider == DEFAULT_LOCAL_PROVIDER:
            return DEFAULT_LOCAL_MODEL

        return None

    def _resolve_policy(
        self,
        request: SkillRunRequest,
        *,
        provider: str,
        preferred_model: Optional[str],
    ) -> ModelPolicy:
        policy_obj = request.input_payload.get("model_policy")
        if isinstance(policy_obj, ModelPolicy):
            return policy_obj

        policy_name = request.input_payload.get("model_policy_ref")

        if policy_name == "anthropic_reasoning":
            return default_anthropic_reasoning_policy()

        if policy_name in {"openai_copy", "openai_for_copy", DEFAULT_COPY_POLICY_REF}:
            return default_openai_copy_policy()

        if provider == "anthropic":
            return default_anthropic_reasoning_policy()

        return default_openai_copy_policy()

    def _maybe_audit_provider_call(
        self,
        *,
        request: SkillRunRequest,
        provider_request: ProviderRequest,
        provider_result,
    ) -> None:
        workspace_id = self._resolve_workspace_id(request, provider_request.metadata)
        if not workspace_id:
            return

        role_id = self._resolve_role_id(request, provider_request.metadata)
        agent_id = request.agent_id or provider_request.metadata.get("agent_id")
        task_id = request.task_id or provider_request.metadata.get("task_id")
        workflow_id = provider_request.metadata.get("workflow_id")

        try:
            self.audit_log.log_provider_call_from_contracts(
                workspace_id=workspace_id,
                request=provider_request,
                result=provider_result,
                role_id=role_id,
                agent_id=agent_id,
                task_id=task_id,
                workflow_id=workflow_id,
            )
        except Exception:
            pass

    @staticmethod
    def _resolve_workspace_id(
        request: SkillRunRequest,
        metadata: Dict[str, Any],
    ) -> Optional[str]:
        workspace_id = metadata.get("workspace_id")
        if isinstance(workspace_id, str) and workspace_id.strip():
            return workspace_id.strip()

        payload_workspace_id = request.input_payload.get("workspace_id")
        if isinstance(payload_workspace_id, str) and payload_workspace_id.strip():
            return payload_workspace_id.strip()

        return None

    @staticmethod
    def _resolve_role_id(
        request: SkillRunRequest,
        metadata: Dict[str, Any],
    ) -> Optional[str]:
        role_id = metadata.get("role_id")
        if isinstance(role_id, str) and role_id.strip():
            return role_id.strip()

        payload_role_id = request.input_payload.get("role_id")
        if isinstance(payload_role_id, str) and payload_role_id.strip():
            return payload_role_id.strip()

        return None

    @staticmethod
    def _build_fallback_content(
        *,
        prompt: str,
        title: Optional[str],
        metadata: Dict[str, Any],
        request: SkillRunRequest,
    ) -> str:
        objective = str(request.objective or "").strip()
        brief = str(
            metadata.get("brief")
            or metadata.get("campaign_brief")
            or metadata.get("offer")
            or objective
            or ""
        ).strip()
        audience = str(metadata.get("target_audience") or "").strip()
        offer = str(metadata.get("offer") or "").strip()
        workspace_name = str(
            metadata.get("workspace_name") or metadata.get("workspace_id") or ""
        ).strip()
        workspace_name = re.sub(r"[-_]+", " ", workspace_name).strip().title()
        cta = str(metadata.get("cta") or "Message us today to get started.").strip()
        hashtags = metadata.get("hashtags") or []
        output_key = str(metadata.get("output_key") or "").strip().lower()

        if output_key == "draft_carousel":
            cards = []

            hook = offer or brief or "Better local service starts here"
            cards.append(hook.rstrip("."))

            if audience:
                cards.append(f"Built around what {audience.lower().rstrip('.')} need to know")
            else:
                cards.append("Built for local homes and businesses")

            cards.append("Share the project, location and any useful photos")
            cards.append(
                f"A person at {workspace_name} reviews the details before anything is promised"
                if workspace_name else
                "A person reviews the details before anything is promised"
            )
            cards.append(cta.rstrip("."))

            return "\n".join(
                card.strip()
                for card in cards[:5]
                if card and str(card).strip()
            )

        lines = []

        if offer:
            lines.append(f"Considering {offer.rstrip('.')}?")
        elif brief:
            lines.append(f"{brief.rstrip('.')}.")

        if audience:
            lines.append(
                f"Tell us what you are planning, where the project is and what matters most. "
                f"This is for {audience.lower().rstrip('.')} who want a clear next step."
            )
        elif brief:
            lines.append("Tell us what you need and share any useful details or photos.")

        if workspace_name:
            lines.append(
                f"A person at {workspace_name} will review the request before any price, "
                "booking or work is confirmed."
            )

        lines.append(cta)

        clean_hashtags = [
            str(tag).strip()
            for tag in hashtags
            if str(tag).strip()
        ]
        if clean_hashtags:
            lines.append(" ".join(clean_hashtags[:5]))

        final_text = "\n\n".join(
            line for line in lines if line and line.strip()
        ).strip()

        if final_text:
            return final_text

        fallback_brief = brief or prompt.strip() or "New local promotion available."
        return f"{fallback_brief.rstrip('.') }.\n\n{cta}".strip()
