from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol

from backend.modules.workflow_capsules.architect.build_pack import WorkflowBuildPack
from backend.modules.workflow_capsules.architect.builder_spec import (
    WorkflowBuilderSpec,
)


@dataclass(slots=True)
class WorkflowBuilderProviderResponse:
    ok: bool
    provider: str
    model: str
    raw_text: str = ""
    spec: WorkflowBuilderSpec | None = None
    requires_clarification: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "provider": self.provider,
            "model": self.model,
            "raw_text": self.raw_text,
            "spec": self.spec.to_dict() if self.spec else None,
            "requires_clarification": self.requires_clarification,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "audit": dict(self.audit),
        }


class WorkflowBuilderProviderAdapter(Protocol):
    provider: str
    model: str

    def build_spec(self, build_pack: WorkflowBuildPack) -> WorkflowBuilderProviderResponse:
        ...


class ProviderJSONParser:
    """
    Strict JSON extraction/parser for provider responses.

    Provider outputs are untrusted. This parser accepts either:
      - raw strict JSON object text
      - fenced JSON block text

    It does not execute anything.
    """

    @staticmethod
    def parse(raw_text: str) -> Dict[str, Any]:
        text = str(raw_text or "").strip()

        if text.startswith("```"):
            text = ProviderJSONParser._strip_fence(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"provider_json_parse_failed:{exc.msg}") from exc

        if not isinstance(data, dict):
            raise ValueError("provider_json_must_be_object")

        return data

    @staticmethod
    def _strip_fence(text: str) -> str:
        lines = text.strip().splitlines()
        if not lines:
            return text

        if lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()


class MockWorkflowBuilderProviderAdapter:
    """
    Local deterministic provider for tests and offline development.

    This simulates an external AI provider returning WorkflowBuilderSpec JSON
    without making any network/API call.
    """

    provider = "mock"
    model = "mock-workflow-builder-v1"

    def __init__(self, response: Dict[str, Any] | str | None = None) -> None:
        self.response = response

    def build_spec(self, build_pack: WorkflowBuildPack) -> WorkflowBuilderProviderResponse:
        if self.response is None:
            response_data = self._default_response(build_pack)
            raw_text = json.dumps(response_data)
        elif isinstance(self.response, dict):
            response_data = self.response
            raw_text = json.dumps(response_data)
        else:
            raw_text = str(self.response)
            try:
                response_data = ProviderJSONParser.parse(raw_text)
            except ValueError as exc:
                return WorkflowBuilderProviderResponse(
                    ok=False,
                    provider=self.provider,
                    model=self.model,
                    raw_text=raw_text,
                    errors=[str(exc)],
                    audit={"build_pack_received": True},
                )

        try:
            spec = WorkflowBuilderSpec.from_dict(response_data)
        except Exception as exc:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                raw_text=raw_text,
                errors=[f"workflow_builder_spec_decode_failed:{type(exc).__name__}:{exc}"],
                audit={"build_pack_received": True},
            )

        return WorkflowBuilderProviderResponse(
            ok=True,
            provider=self.provider,
            model=self.model,
            raw_text=raw_text,
            spec=spec,
            requires_clarification=bool(spec.requires_clarification),
            audit={
                "build_pack_received": True,
                "business_context_present": bool(build_pack.business_context),
                "node_registry_present": bool(build_pack.node_registry),
                "schema_version": spec.schema_version,
                "step_count": len(spec.steps),
                "edge_count": len(spec.edges),
            },
        )

    @staticmethod
    def _default_response(build_pack: WorkflowBuildPack) -> Dict[str, Any]:
        goal = str(build_pack.user_task.get("workflow_goal") or "Generated workflow")
        connected = set(build_pack.credentials.get("connected") or [])
        missing = set(build_pack.credentials.get("missing") or [])

        connectors_required = ["gmail"]
        missing_connectors = []

        if "hubspot" in connected or "hubspot" in missing:
            connectors_required.append("hubspot")
            if "hubspot" in missing:
                missing_connectors.append(
                    {
                        "connector": "hubspot",
                        "reason": "HubSpot is required but not connected.",
                        "step_id": "hubspot_placeholder",
                    }
                )

        return {
            "schema_version": "aion.workflow_builder_spec.v1",
            "workflow_name": "Mock Generated Gmail Workflow",
            "goal": goal,
            "requires_clarification": False,
            "clarification_questions": [],
            "connectors_required": connectors_required,
            "missing_connectors": missing_connectors,
            "must_not_do": ["do not send live emails"],
            "steps": [
                {
                    "step_id": "read_gmail",
                    "node_type": "gmail.read",
                    "label": "Read Gmail",
                    "connector": "gmail",
                    "config": {
                        "account": "newcustomer@example.com",
                        "trigger": "new_email",
                    },
                    "risk_tier": "low",
                    "requires_approval": False,
                },
                {
                    "step_id": "extract_fields",
                    "node_type": "extract_fields",
                    "label": "Extract customer fields",
                    "config": {
                        "fields": ["name", "email", "phone"],
                    },
                    "risk_tier": "low",
                    "requires_approval": False,
                },
                {
                    "step_id": "compose_reply",
                    "node_type": "compose_string",
                    "label": "Compose reply",
                    "config": {
                        "template_ref": "welcome_email_template",
                    },
                    "risk_tier": "low",
                    "requires_approval": False,
                },
                {
                    "step_id": "approval",
                    "node_type": "human_approval",
                    "label": "Approve draft",
                    "config": {
                        "reason": "Approval required before customer-facing draft.",
                    },
                    "risk_tier": "medium",
                    "requires_approval": True,
                },
                {
                    "step_id": "create_draft",
                    "node_type": "gmail.create_draft",
                    "label": "Create Gmail draft",
                    "connector": "gmail",
                    "config": {
                        "to": "{{extract_fields.email}}",
                        "body": "{{compose_reply.output}}",
                    },
                    "risk_tier": "medium",
                    "requires_approval": True,
                },
            ],
            "edges": [
                ["read_gmail", "extract_fields"],
                ["extract_fields", "compose_reply"],
                ["compose_reply", "approval"],
                ["approval", "create_draft"],
            ],
        }


class PlaceholderWorkflowBuilderProviderAdapter:
    """
    Placeholder for real providers not yet wired.

    This makes provider selection explicit while failing closed until an actual
    adapter is implemented.
    """

    def __init__(self, *, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model

    def build_spec(self, build_pack: WorkflowBuildPack) -> WorkflowBuilderProviderResponse:
        return WorkflowBuilderProviderResponse(
            ok=False,
            provider=self.provider,
            model=self.model,
            errors=[f"provider_not_implemented:{self.provider}"],
            audit={
                "build_pack_received": True,
                "fail_closed": True,
            },
        )
