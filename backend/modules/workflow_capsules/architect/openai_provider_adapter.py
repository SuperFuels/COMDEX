from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict

from backend.modules.workflow_capsules.architect.build_pack import WorkflowBuildPack
from backend.modules.workflow_capsules.architect.builder_spec import WorkflowBuilderSpec
from backend.modules.workflow_capsules.architect.provider_adapter import (
    ProviderJSONParser,
    WorkflowBuilderProviderResponse,
)


class OpenAIWorkflowBuilderProviderAdapter:
    """
    Env-gated OpenAI provider adapter for Workflow Architect.

    Fail-closed rules:
    - no API key => no network call
    - network disabled => no network call
    - provider output must be strict JSON
    - provider output is still untrusted and must pass Aion validation/review/dry-run
    """

    provider = "openai"

    def __init__(
        self,
        *,
        model: str = "gpt-5.1",
        api_key: str | None = None,
        allow_network: bool | None = None,
        raw_response_text: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.raw_response_text = raw_response_text

        if allow_network is None:
            allow_network = os.getenv("AION_WORKFLOW_ARCHITECT_OPENAI_NETWORK", "").lower() in {
                "1",
                "true",
                "yes",
            }

        self.allow_network = bool(allow_network)

    def build_spec(self, build_pack: WorkflowBuildPack) -> WorkflowBuilderProviderResponse:
        if not self.api_key:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                errors=["provider_not_configured:openai"],
                warnings=["openai_api_key_missing"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": False,
                    "strict_json_only": True,
                },
            )

        if self.raw_response_text is not None:
            return self._parse_response(
                self.raw_response_text,
                build_pack,
                network_call_attempted=False,
            )

        if os.getenv("AION_WORKFLOW_ARCHITECT_OPENAI_LIVE_UNLOCK", "").lower() not in {"1", "true", "yes"}:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                errors=["provider_network_disabled:openai"],
                warnings=["openai_network_call_blocked_by_default"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": False,
                    "strict_json_only": True,
                },
            )

        if not self.allow_network:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                errors=["provider_network_disabled:openai"],
                warnings=["openai_network_call_blocked_by_default"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": False,
                    "strict_json_only": True,
                },
            )

        raw_text = self._call_openai(build_pack)
        if raw_text.startswith("__OPENAI_ERROR__:"):
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                raw_text=raw_text,
                errors=[raw_text.replace("__OPENAI_ERROR__:", "", 1)],
                warnings=[],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": True,
                    "strict_json_only": True,
                },
            )

        return self._parse_response(
            raw_text,
            build_pack,
            network_call_attempted=True,
        )

    def _call_openai(self, build_pack: WorkflowBuildPack) -> str:
        system_prompt = (
            "You are Aion Workflow Architect. "
            "Return ONLY strict JSON matching aion.workflow_builder_spec.v1. "
            "Do not return markdown. Do not invent unsupported node types. "
            "Use only node types from build_pack.node_registry. "
            "Use build_pack.connector_catalogue and build_pack.connector_build_rules for connector policy. "
            "For Gmail, prefer gmail.create_draft when preparing emails. "
            "Never use gmail.send_email, gmail.reply_email, or gmail.send_draft by default; "
            "they are visible locked capabilities only and live sending is future-only. "
            "Use human_approval before external writes, missing_connector_placeholder for unavailable integrations, "
            "and keep all external writes dry-run-first."
        )

        user_prompt = {
            "instruction": "Build a safe WorkflowBuilderSpec JSON object from this build pack.",
            "build_pack": build_pack.to_dict(),
        }

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_prompt, ensure_ascii=False),
                },
            ],
            "text": {
                "format": {
                    "type": "json_object",
                }
            },
        }

        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return f"__OPENAI_ERROR__:openai_http_error:{exc.code}:{body}"
        except Exception as exc:
            return f"__OPENAI_ERROR__:openai_request_failed:{type(exc).__name__}:{exc}"

        output_text = self._extract_output_text(response_data)
        if not output_text:
            return f"__OPENAI_ERROR__:openai_empty_output:{json.dumps(response_data)[:1000]}"

        return output_text

    @staticmethod
    def _extract_output_text(response_data: Dict[str, Any]) -> str:
        if isinstance(response_data.get("output_text"), str):
            return response_data["output_text"].strip()

        chunks: list[str] = []
        for item in response_data.get("output", []) or []:
            for content in item.get("content", []) or []:
                if isinstance(content.get("text"), str):
                    chunks.append(content["text"])
                elif isinstance(content.get("json"), dict):
                    chunks.append(json.dumps(content["json"]))

        return "\n".join(chunks).strip()

    @staticmethod
    def _normalise_provider_spec(
        parsed: Dict[str, Any],
        build_pack: WorkflowBuildPack,
    ) -> Dict[str, Any]:
        """
        Deterministic provider-output cleanup.

        This does not trust or accept the workflow. It only removes malformed
        provider JSON noise and normalises known safety metadata before the
        normal validator/review/dry-run path runs.
        """
        spec = dict(parsed or {})
        steps = list(spec.get("steps") or [])

        step_ids = {
            str(step.get("step_id") or "").strip()
            for step in steps
            if isinstance(step, dict) and str(step.get("step_id") or "").strip()
        }

        normalised_steps = []
        for step in steps:
            if not isinstance(step, dict):
                continue

            item = dict(step)
            node_type = str(item.get("node_type") or "").strip()
            step_id = str(item.get("step_id") or "").strip()

            if not step_id or not node_type:
                continue

            config = item.get("config")
            if not isinstance(config, dict):
                config = {}

            if node_type == "missing_connector_placeholder":
                item["missing_connector"] = True
                item["risk_tier"] = "blocked"
                item["requires_approval"] = False
                if not item.get("connector"):
                    item["connector"] = config.get("connector") or step_id.replace("_placeholder", "")

            if node_type == "human_approval":
                item["risk_tier"] = "medium"
                item["requires_approval"] = True

            if node_type in {"gmail.create_draft", "hubspot.upsert_contact"}:
                item["risk_tier"] = "medium"
                item["requires_approval"] = True

            if node_type == "gmail.live_send":
                # Keep this unsafe node visible to the validator. Do not rewrite it.
                item["risk_tier"] = "high"
                item["requires_approval"] = True

            item["config"] = config
            normalised_steps.append(item)

        spec["steps"] = normalised_steps

        step_ids = {
            str(step.get("step_id") or "").strip()
            for step in normalised_steps
            if isinstance(step, dict) and str(step.get("step_id") or "").strip()
        }

        valid_edges = []
        for edge in list(spec.get("edges") or []):
            source = ""
            target = ""
            condition = None

            if isinstance(edge, dict):
                source = str(edge.get("source") or "").strip()
                target = str(edge.get("target") or "").strip()
                condition = edge.get("condition")
            elif isinstance(edge, (list, tuple)) and len(edge) >= 2:
                source = str(edge[0] or "").strip()
                target = str(edge[1] or "").strip()

            if not source or not target:
                continue

            if source not in step_ids or target not in step_ids:
                continue

            valid_edges.append(
                {
                    "source": source,
                    "target": target,
                    "condition": condition,
                }
            )

        if not valid_edges and len(normalised_steps) > 1:
            for left, right in zip(normalised_steps, normalised_steps[1:]):
                valid_edges.append(
                    {
                        "source": str(left["step_id"]),
                        "target": str(right["step_id"]),
                        "condition": None,
                    }
                )

        spec["edges"] = valid_edges

        connectors_required = set(spec.get("connectors_required") or [])
        for step in normalised_steps:
            connector = step.get("connector")
            if connector and step.get("node_type") != "missing_connector_placeholder":
                connectors_required.add(str(connector))

        spec["connectors_required"] = sorted(connectors_required)

        return spec


    def _parse_response(
        self,
        raw_text: str,
        build_pack: WorkflowBuildPack,
        *,
        network_call_attempted: bool,
    ) -> WorkflowBuilderProviderResponse:
        try:
            parsed: Dict[str, Any] = ProviderJSONParser.parse(raw_text)
        except ValueError as exc:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                raw_text=raw_text,
                errors=[str(exc)],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": network_call_attempted,
                    "strict_json_only": True,
                },
            )

        parsed = self._normalise_provider_spec(parsed, build_pack)

        try:
            spec = WorkflowBuilderSpec.from_dict(parsed)
        except Exception as exc:
            return WorkflowBuilderProviderResponse(
                ok=False,
                provider=self.provider,
                model=self.model,
                raw_text=raw_text,
                errors=[f"workflow_builder_spec_decode_failed:{type(exc).__name__}:{exc}"],
                audit={
                    "build_pack_received": True,
                    "network_call_attempted": network_call_attempted,
                    "strict_json_only": True,
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
                "network_call_attempted": network_call_attempted,
                "strict_json_only": True,
                "schema_version": spec.schema_version,
                "step_count": len(spec.steps),
                "edge_count": len(spec.edges),
                "node_registry_present": bool(build_pack.node_registry),
            },
        )
