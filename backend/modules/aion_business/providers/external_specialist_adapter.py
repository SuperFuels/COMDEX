from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.external_specialists import (
    ExternalSpecialistSpec,
)
from backend.modules.aion_business.contracts.external_work_orders import (
    ExternalWorkOrderRecord,
)
from backend.modules.aion_business.providers.contracts import (
    ProviderRequest,
    ProviderResult,
)
from backend.modules.aion_business.providers.mailchimp_adapter import (
    MailchimpAdapter,
)
from backend.modules.aion_business.providers.router import ProviderRouter
from backend.modules.aion_business.runtime.external_work_order_manager import (
    ExternalWorkOrderManager,
)


@dataclass(slots=True)
class ExternalSpecialistExecutionResult:
    ok: bool
    execution_mode: str
    specialist_id: Optional[str]
    specialist_type: Optional[str]
    provider_result: Optional[ProviderResult] = None
    work_order: Optional[ExternalWorkOrderRecord] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExternalSpecialistAdapter:
    """
    Routes execution by specialist type.

    supported:
    - provider_model: uses existing ProviderRouter immediately
    - native_platform_ai:
        - mailchimp -> real adapter path
        - others -> stub via external work order
    - external_service: stub -> creates/dispatched external work order
    - human_specialist: creates/dispatched external work order
    """

    def __init__(
        self,
        *,
        provider_router: Optional[ProviderRouter] = None,
        external_work_order_manager: Optional[ExternalWorkOrderManager] = None,
        mailchimp_adapter: Optional[MailchimpAdapter] = None,
    ):
        self.provider_router = provider_router or ProviderRouter()
        self.external_work_order_manager = (
            external_work_order_manager or ExternalWorkOrderManager()
        )
        self.mailchimp_adapter = mailchimp_adapter or MailchimpAdapter()

    def execute(
        self,
        *,
        workspace_id: str,
        specialist: ExternalSpecialistSpec,
        capability: str,
        objective: str,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        role_type: Optional[str] = None,
        skill_id: Optional[str] = None,
        model_policy_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_tokens: int = 512,
        input_payload: Optional[Dict[str, Any]] = None,
    ) -> ExternalSpecialistExecutionResult:
        input_payload = input_payload or {}
        metadata = metadata or {}

        if specialist.specialist_type == "provider_model":
            return self._execute_provider_model(
                specialist=specialist,
                capability=capability,
                prompt=prompt,
                system_prompt=system_prompt,
                role_type=role_type,
                skill_id=skill_id,
                model_policy_ref=model_policy_ref,
                metadata=metadata,
                max_tokens=max_tokens,
            )

        if specialist.specialist_type == "native_platform_ai":
            if specialist.provider == "mailchimp":
                return self._execute_mailchimp(
                    specialist=specialist,
                    capability=capability,
                    objective=objective,
                    metadata=metadata,
                    input_payload=input_payload,
                )

            return self._create_stub_work_order(
                workspace_id=workspace_id,
                specialist=specialist,
                capability=capability,
                objective=objective,
                prompt=prompt,
                system_prompt=system_prompt,
                parent_task_id=parent_task_id,
                metadata=metadata,
            )

        if specialist.specialist_type == "external_service":
            return self._create_stub_work_order(
                workspace_id=workspace_id,
                specialist=specialist,
                capability=capability,
                objective=objective,
                prompt=prompt,
                system_prompt=system_prompt,
                parent_task_id=parent_task_id,
                metadata=metadata,
            )

        if specialist.specialist_type == "human_specialist":
            return self._create_stub_work_order(
                workspace_id=workspace_id,
                specialist=specialist,
                capability=capability,
                objective=objective,
                prompt=prompt,
                system_prompt=system_prompt,
                parent_task_id=parent_task_id,
                metadata=metadata,
            )

        return ExternalSpecialistExecutionResult(
            ok=False,
            execution_mode="unknown",
            specialist_id=specialist.id,
            specialist_type=specialist.specialist_type,
            error_code=f"unsupported_specialist_type:{specialist.specialist_type}",
            metadata=metadata,
        )

    def _execute_provider_model(
        self,
        *,
        specialist: ExternalSpecialistSpec,
        capability: str,
        prompt: Optional[str],
        system_prompt: Optional[str],
        role_type: Optional[str],
        skill_id: Optional[str],
        model_policy_ref: Optional[str],
        metadata: Dict[str, Any],
        max_tokens: int,
    ) -> ExternalSpecialistExecutionResult:
        if not prompt:
            return ExternalSpecialistExecutionResult(
                ok=False,
                execution_mode="provider_model",
                specialist_id=specialist.id,
                specialist_type=specialist.specialist_type,
                error_code="missing_prompt_for_provider_model",
                metadata=metadata,
            )

        provider_result = self.provider_router.generate_from_request(
            ProviderRequest(
                provider=specialist.provider,
                prompt=prompt,
                system_prompt=system_prompt,
                capability=capability,  # type: ignore[arg-type]
                role_type=role_type,
                skill_id=skill_id,
                policy_id=model_policy_ref,
                metadata=metadata,
                max_tokens=max_tokens,
            ),
            policy_ref=model_policy_ref,
        )

        return ExternalSpecialistExecutionResult(
            ok=provider_result.ok,
            execution_mode="provider_model",
            specialist_id=specialist.id,
            specialist_type=specialist.specialist_type,
            provider_result=provider_result,
            error_code=provider_result.error_code,
            metadata=metadata,
        )

    def _execute_mailchimp(
        self,
        *,
        specialist: ExternalSpecialistSpec,
        capability: str,
        objective: str,
        metadata: Dict[str, Any],
        input_payload: Dict[str, Any],
    ) -> ExternalSpecialistExecutionResult:
        if capability == "mailchimp_upsert_contact":
            result = self.mailchimp_adapter.upsert_contact(
                list_id=str(input_payload.get("list_id", "")),
                email=str(input_payload.get("email", "")),
                status_if_new=str(input_payload.get("status_if_new", "subscribed")),
                merge_fields=dict(input_payload.get("merge_fields", {})),
                tags=list(input_payload.get("tags", [])),
                metadata=metadata,
            )
            return self._mailchimp_result_to_execution(
                specialist=specialist,
                result=result,
                execution_mode="native_platform_ai",
                objective=objective,
                metadata=metadata,
            )

        if capability == "mailchimp_create_campaign_draft":
            result = self.mailchimp_adapter.create_campaign_draft(
                list_id=str(input_payload.get("list_id", "")),
                subject_line=str(input_payload.get("subject_line", "")),
                title=str(input_payload.get("title", "")),
                from_name=str(input_payload.get("from_name", "")),
                reply_to=str(input_payload.get("reply_to", "")),
                html=str(input_payload.get("html", "")),
                metadata=metadata,
            )
            return self._mailchimp_result_to_execution(
                specialist=specialist,
                result=result,
                execution_mode="native_platform_ai",
                objective=objective,
                metadata=metadata,
            )

        return ExternalSpecialistExecutionResult(
            ok=False,
            execution_mode="native_platform_ai",
            specialist_id=specialist.id,
            specialist_type=specialist.specialist_type,
            error_code=f"unsupported_mailchimp_capability:{capability}",
            metadata={"objective": objective, **metadata},
        )

    def _mailchimp_result_to_execution(
        self,
        *,
        specialist: ExternalSpecialistSpec,
        result,
        execution_mode: str,
        objective: str,
        metadata: Dict[str, Any],
    ) -> ExternalSpecialistExecutionResult:
        provider_result = ProviderResult(
            ok=result.ok,
            provider=result.provider,
            model=result.action,
            content=result.content,
            usage=dict(result.usage or {}),
            latency_ms=result.latency_ms,
            fallback_used=False,
            error_code=result.error_code,
            raw=result.raw,
            policy_id=None,
            warnings=[result.error_code] if result.error_code else [],
        )

        return ExternalSpecialistExecutionResult(
            ok=result.ok,
            execution_mode=execution_mode,
            specialist_id=specialist.id,
            specialist_type=specialist.specialist_type,
            provider_result=provider_result,
            error_code=result.error_code,
            metadata={"objective": objective, **metadata},
        )

    def _create_stub_work_order(
        self,
        *,
        workspace_id: str,
        specialist: ExternalSpecialistSpec,
        capability: str,
        objective: str,
        prompt: Optional[str],
        system_prompt: Optional[str],
        parent_task_id: Optional[str],
        metadata: Dict[str, Any],
    ) -> ExternalSpecialistExecutionResult:
        work_order = self.external_work_order_manager.create_work_order(
            workspace_id=workspace_id,
            capability=capability,
            objective=objective,
            parent_task_id=parent_task_id,
            inputs={
                "prompt": prompt or "",
                "system_prompt": system_prompt or "",
                "specialist_id": specialist.id,
                "specialist_type": specialist.specialist_type,
                "provider": specialist.provider,
            },
            metadata=metadata,
        )
        work_order = self.external_work_order_manager.dispatch(workspace_id, work_order.id)

        return ExternalSpecialistExecutionResult(
            ok=True,
            execution_mode=specialist.specialist_type,
            specialist_id=specialist.id,
            specialist_type=specialist.specialist_type,
            work_order=work_order,
            metadata=metadata,
        )