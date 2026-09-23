from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.modules.workflow_capsules.architect.build_pack import WorkflowBuildPack
from backend.modules.workflow_capsules.architect.builder_spec import WorkflowBuilderSpec
from backend.modules.workflow_capsules.architect.provider_adapter import (
    ProviderJSONParser,
    WorkflowBuilderProviderResponse,
)


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_GEMMA_MODEL = "gemma4:e2b"


@dataclass(slots=True)
class LocalGemmaWorkflowBuilderProviderAdapter:
    """
    Local Ollama/Gemma workflow builder adapter.

    This adapter follows the same safety contract as the OpenAI adapter:
    provider proposes only, strict JSON only, no direct execution, no live send.
    """

    model: str = DEFAULT_GEMMA_MODEL
    base_url: Optional[str] = None
    enabled: Optional[bool] = None
    timeout_seconds: float = 30.0
    raw_response_text: Optional[str] = None

    provider: str = "local_gemma"

    def _is_enabled(self) -> bool:
        if self.enabled is not None:
            return bool(self.enabled)

        value = str(os.getenv("AION_LOCAL_GEMMA_ENABLED", "")).strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _base_url(self) -> str:
        return str(
            self.base_url
            or os.getenv("AION_OLLAMA_BASE_URL")
            or DEFAULT_OLLAMA_BASE_URL
        ).rstrip("/")

    def build_spec(self, build_pack: WorkflowBuildPack) -> WorkflowBuilderProviderResponse:
        if not self._is_enabled() and self.raw_response_text is None:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                errors=["provider_not_configured:local_gemma"],
                warnings=["local_gemma_disabled_or_unconfigured"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": False,
                    "strict_json_only": True,
                    "local_provider": True,
                },
            )

        if self.raw_response_text is not None:
            raw_text = self.raw_response_text
        else:
            try:
                raw_text = self._call_ollama(build_pack)
            except Exception as exc:
                return WorkflowBuilderProviderResponse(
                    ok=False,
                    provider=self.provider,
                    model=self.model,
                    errors=[f"local_gemma_call_failed:{type(exc).__name__}:{exc}"],
                    warnings=["provider_failed_closed"],
                    audit={
                        "build_pack_received": True,
                        "network_call_attempted": True,
                        "strict_json_only": True,
                        "local_provider": True,
                    },
                )

        try:
            data = ProviderJSONParser.parse(raw_text)
        except ValueError as exc:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                raw_text=raw_text,
                errors=[str(exc)],
                warnings=["provider_json_rejected"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": self.raw_response_text is None,
                    "strict_json_only": True,
                    "local_provider": True,
                },
            )

        try:
            spec = WorkflowBuilderSpec.from_dict(data)
        except Exception as exc:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                raw_text=raw_text,
                errors=[f"workflow_builder_spec_decode_failed:{type(exc).__name__}:{exc}"],
                warnings=["provider_spec_rejected"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": self.raw_response_text is None,
                    "strict_json_only": True,
                    "local_provider": True,
                },
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
                "strict_json_only": True,
                "network_call_attempted": self.raw_response_text is None,
                "local_provider": True,
                "ollama_base_url": self._base_url(),
                "schema_version": spec.schema_version,
                "step_count": len(spec.steps),
                "edge_count": len(spec.edges),
            },
        )

    def _call_ollama(self, build_pack: WorkflowBuildPack) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "prompt": self._prompt(build_pack),
            "options": {
                "temperature": 0,
            },
        }

        request = urllib.request.Request(
            f"{self._base_url()}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")

        data = json.loads(body)
        return str(data.get("response") or "")

    @staticmethod
    def _prompt(build_pack: WorkflowBuildPack) -> str:
        return (
            "You are AION Workflow Architect running locally through Ollama/Gemma.\n"
            "Return strict JSON only. No markdown. No prose. No code fences.\n"
            "You must output one WorkflowBuilderSpec JSON object.\n"
            "Use only approved node types from the provided node registry.\n"
            "Use the connector_catalogue and connector_build_rules for connector policy.\n"
            "For Gmail, prefer gmail.create_draft when preparing emails.\n"
            "Do not use gmail.send_email, gmail.reply_email, or gmail.send_draft by default; "
            "they are locked future-only capabilities.\n"
            "Do not invent node types. Do not include live_send, send_message, "
            "users.messages.send, or live_execute.\n"
            "External writes must require human approval and remain dry-run-first.\n\n"
            "WorkflowBuildPack JSON:\n"
            + json.dumps(build_pack.to_dict(), sort_keys=True)
        )
