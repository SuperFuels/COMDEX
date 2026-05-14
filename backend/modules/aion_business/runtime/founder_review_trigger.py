from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.modules.aion_business.providers.resend_actions import ResendActions
from backend.modules.aion_business.providers.resend_adapter import ResendAdapter
from backend.modules.aion_business.runtime.audit_log import AuditLog
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.role_repository import RoleRepository
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository
from backend.modules.aion_business.workflows.weekly_founder_review import (
    WeeklyFounderReviewWorkflow,
)


class FounderReviewTriggerConfig(BaseModel):
    workspace_id: str
    role_id: str = "ceo-core"
    enabled: bool = True
    cadence: str = "weekly"
    days_back: int = Field(default=7, ge=1, le=365)
    include_draft: bool = True
    send_email: bool = False
    send_to_emails: List[str] = Field(default_factory=list)
    from_email: Optional[str] = None
    last_run_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class FounderReviewTriggerResult:
    config: FounderReviewTriggerConfig
    workflow_result: Any


class FounderReviewTrigger:
    """
    Small trigger runner for weekly founder review.

    v2 responsibilities:
    - persist per-workspace trigger config
    - manually invoke founder review from one place
    - optionally deliver the founder review by email
    - provide a clean runtime surface for later scheduler wiring
    - write audit events when trigger fires / completes / fails

    Storage layout:
    .runtime/AION_BUSINESS/founder_review_triggers/<workspace_id>.json
    """

    def __init__(
        self,
        *,
        workspace_repository: Optional[WorkspaceRepository] = None,
        role_repository: Optional[RoleRepository] = None,
        workflow: Optional[WeeklyFounderReviewWorkflow] = None,
        audit_log: Optional[AuditLog] = None,
        resend_actions: Optional[ResendActions] = None,
    ):
        self.workspace_repository = workspace_repository or WorkspaceRepository()
        self.role_repository = role_repository or RoleRepository()
        self.workflow = workflow or WeeklyFounderReviewWorkflow()
        self.audit_log = audit_log or AuditLog()
        self.resend_actions = resend_actions or ResendActions(
            resend_adapter=ResendAdapter()
        )
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        AIONBusinessPaths.ensure_base_dirs()
        self._trigger_root().mkdir(parents=True, exist_ok=True)

    def _trigger_root(self) -> Path:
        return AIONBusinessPaths.ROOT / "founder_review_triggers"

    def _trigger_file(self, workspace_id: str) -> Path:
        return self._trigger_root() / f"{workspace_id}.json"

    def save_config(self, config: FounderReviewTriggerConfig) -> Path:
        path = self._trigger_file(config.workspace_id)
        path.write_text(
            json.dumps(config.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load_config(self, workspace_id: str) -> FounderReviewTriggerConfig:
        path = self._trigger_file(workspace_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Founder review trigger config not found: {workspace_id}"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return FounderReviewTriggerConfig(**data)

    def get_or_create_config(
        self,
        *,
        workspace_id: str,
        role_id: str = "ceo-core",
        days_back: int = 7,
        include_draft: bool = True,
        enabled: bool = True,
        send_email: bool = False,
        send_to_emails: Optional[List[str]] = None,
        from_email: Optional[str] = None,
    ) -> FounderReviewTriggerConfig:
        path = self._trigger_file(workspace_id)
        if path.exists():
            return self.load_config(workspace_id)

        config = FounderReviewTriggerConfig(
            workspace_id=workspace_id,
            role_id=role_id,
            enabled=enabled,
            cadence="weekly",
            days_back=days_back,
            include_draft=include_draft,
            send_email=send_email,
            send_to_emails=send_to_emails or [],
            from_email=from_email,
        )
        self.save_config(config)
        return config

    def run_weekly_review(
        self,
        *,
        workspace_id: str,
        role_id: str = "ceo-core",
        days_back: int = 7,
        include_draft: bool = True,
        persist_config: bool = True,
        send_email: bool = False,
        send_to_emails: Optional[List[str]] = None,
        from_email: Optional[str] = None,
    ) -> FounderReviewTriggerResult:
        config = self.get_or_create_config(
            workspace_id=workspace_id,
            role_id=role_id,
            days_back=days_back,
            include_draft=include_draft,
            enabled=True,
            send_email=send_email,
            send_to_emails=send_to_emails,
            from_email=from_email,
        )

        if persist_config:
            config.role_id = role_id
            config.days_back = days_back
            config.include_draft = include_draft
            config.send_email = send_email
            config.send_to_emails = send_to_emails or config.send_to_emails
            config.from_email = from_email or config.from_email
            self.save_config(config)

        if not config.enabled:
            self.audit_log.log_event(
                workspace_id=workspace_id,
                event_type="workflow_trigger_skipped",
                role_id=config.role_id,
                summary="Weekly founder review trigger skipped because it is disabled",
                payload={
                    "workflow_id": "weekly-founder-review",
                    "cadence": config.cadence,
                },
                tags=["trigger", "weekly_founder_review", "skipped"],
            )
            raise ValueError(
                f"Founder review trigger is disabled for workspace: {workspace_id}"
            )

        workspace = self.workspace_repository.load(workspace_id)
        role = self.role_repository.load(workspace_id, config.role_id)

        self.audit_log.log_event(
            workspace_id=workspace_id,
            event_type="workflow_triggered",
            role_id=role.id,
            workflow_id="weekly-founder-review",
            summary="Weekly founder review trigger fired",
            payload={
                "workflow_id": "weekly-founder-review",
                "cadence": config.cadence,
                "days_back": config.days_back,
                "include_draft": config.include_draft,
                "send_email": config.send_email,
                "send_to_emails": config.send_to_emails,
                "from_email": config.from_email,
            },
            tags=["trigger", "weekly_founder_review", "fired"],
        )

        try:
            workflow_result = self.workflow.run(
                workspace=workspace,
                role=role,
                days_back=config.days_back,
                include_draft=config.include_draft,
            )

            config.last_run_at = workflow_result.completed_at or workflow_result.updated_at
            if persist_config:
                self.save_config(config)

            if config.send_email and config.send_to_emails:
                summary_text = self._extract_founder_summary_text(workflow_result)

                send_result = self.resend_actions.send_founder_summary(
                    to_emails=config.send_to_emails,
                    workspace_name=workspace.name,
                    summary_text=summary_text or f"{workspace.name} founder review completed.",
                    from_email=config.from_email,
                )

                if send_result.ok:
                    self.audit_log.log_event(
                        workspace_id=workspace_id,
                        event_type="custom",
                        role_id=role.id,
                        workflow_id="weekly-founder-review",
                        summary="Founder review email sent",
                        payload={
                            "workflow_id": "weekly-founder-review",
                            "run_id": workflow_result.id,
                            "provider": send_result.provider,
                            "model": send_result.model,
                            "content": send_result.content,
                            "to_emails": config.send_to_emails,
                            "from_email": config.from_email,
                        },
                        tags=["trigger", "weekly_founder_review", "email_sent"],
                    )
                else:
                    self.audit_log.log_event(
                        workspace_id=workspace_id,
                        event_type="custom",
                        role_id=role.id,
                        workflow_id="weekly-founder-review",
                        summary="Founder review email send failed",
                        payload={
                            "workflow_id": "weekly-founder-review",
                            "run_id": workflow_result.id,
                            "error_code": send_result.error_code,
                            "to_emails": config.send_to_emails,
                            "from_email": config.from_email,
                            "raw": send_result.raw,
                        },
                        tags=["trigger", "weekly_founder_review", "email_failed"],
                    )

            self.audit_log.log_event(
                workspace_id=workspace_id,
                event_type="workflow_trigger_completed",
                role_id=role.id,
                workflow_id="weekly-founder-review",
                summary="Weekly founder review trigger completed",
                payload={
                    "workflow_id": "weekly-founder-review",
                    "run_id": workflow_result.id,
                    "status": workflow_result.status,
                    "send_email": config.send_email,
                },
                tags=["trigger", "weekly_founder_review", "completed"],
            )

            return FounderReviewTriggerResult(
                config=config,
                workflow_result=workflow_result,
            )

        except Exception as exc:
            self.audit_log.log_event(
                workspace_id=workspace_id,
                event_type="workflow_trigger_failed",
                role_id=role.id,
                workflow_id="weekly-founder-review",
                summary="Weekly founder review trigger failed",
                payload={
                    "workflow_id": "weekly-founder-review",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                tags=["trigger", "weekly_founder_review", "failed"],
            )
            raise

    def _extract_founder_summary_text(self, workflow_result: Any) -> str:
        outputs = getattr(workflow_result, "outputs", {}) or {}

        draft = (outputs.get("draft_content", {}) or {}).get("draft", "")
        if draft and str(draft).strip():
            return str(draft).strip()

        report = (outputs.get("produce_report", {}) or {}).get("report", {}) or {}
        summary = report.get("summary", "")
        highlights = report.get("highlights", []) or []

        lines: List[str] = []
        if summary:
            lines.append(str(summary).strip())

        if highlights:
            lines.append("")
            lines.append("Highlights:")
            for item in highlights[:8]:
                if isinstance(item, dict):
                    if "text" in item:
                        lines.append(f"- {item['text']}")
                    elif "key" in item and "value" in item:
                        lines.append(f"- {item['key']}: {item['value']}")
                    elif "key" in item and "count" in item:
                        lines.append(f"- {item['key']} count: {item['count']}")
                    else:
                        lines.append(f"- {item}")
                else:
                    lines.append(f"- {item}")

        return "\n".join(lines).strip()

    def set_enabled(self, *, workspace_id: str, enabled: bool) -> FounderReviewTriggerConfig:
        config = self.load_config(workspace_id)
        config.enabled = enabled
        self.save_config(config)
        return config

    def update_config(
        self,
        *,
        workspace_id: str,
        role_id: Optional[str] = None,
        days_back: Optional[int] = None,
        include_draft: Optional[bool] = None,
        enabled: Optional[bool] = None,
        cadence: Optional[str] = None,
        send_email: Optional[bool] = None,
        send_to_emails: Optional[List[str]] = None,
        from_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FounderReviewTriggerConfig:
        config = self.load_config(workspace_id)

        if role_id is not None:
            config.role_id = role_id
        if days_back is not None:
            config.days_back = days_back
        if include_draft is not None:
            config.include_draft = include_draft
        if enabled is not None:
            config.enabled = enabled
        if cadence is not None:
            config.cadence = cadence
        if send_email is not None:
            config.send_email = send_email
        if send_to_emails is not None:
            config.send_to_emails = send_to_emails
        if from_email is not None:
            config.from_email = from_email
        if metadata is not None:
            config.metadata = metadata

        self.save_config(config)
        return config