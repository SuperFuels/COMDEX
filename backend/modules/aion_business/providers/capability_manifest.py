from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


PROVIDER_CAPABILITY_MANIFEST_SCHEMA_VERSION = "aion.business.provider_capability_manifest.v1"


@dataclass(frozen=True)
class ProviderCapabilityManifest:
    provider: str
    default_model: str
    configured: bool = False
    capabilities: List[str] = field(default_factory=list)
    enhanced_mode: bool = False
    supports_long_running_sessions: bool = False
    supports_checkpoint_resume: bool = False
    supports_sandboxed_execution: bool = False
    supports_outcome_evaluation: bool = False
    supports_memory_dreaming: bool = False
    supports_multi_agent_orchestration: bool = False
    supports_mcp_private_connectors: bool = False
    max_tokens: int = 0
    max_cost_per_task: float = 0.0
    runtime_limits: Dict[str, Any] = field(default_factory=dict)
    fallback_provider: str | None = None
    degradation_mode: str = "fail_closed"
    disclosure: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": PROVIDER_CAPABILITY_MANIFEST_SCHEMA_VERSION,
            "provider": self.provider,
            "default_model": self.default_model,
            "configured": bool(self.configured),
            "capabilities": list(self.capabilities),
            "enhanced_mode": bool(self.enhanced_mode),
            "supports_long_running_sessions": bool(self.supports_long_running_sessions),
            "supports_checkpoint_resume": bool(self.supports_checkpoint_resume),
            "supports_sandboxed_execution": bool(self.supports_sandboxed_execution),
            "supports_outcome_evaluation": bool(self.supports_outcome_evaluation),
            "supports_memory_dreaming": bool(self.supports_memory_dreaming),
            "supports_multi_agent_orchestration": bool(self.supports_multi_agent_orchestration),
            "supports_mcp_private_connectors": bool(self.supports_mcp_private_connectors),
            "max_tokens": int(self.max_tokens or 0),
            "max_cost_per_task": float(self.max_cost_per_task or 0.0),
            "runtime_limits": dict(self.runtime_limits),
            "fallback_provider": self.fallback_provider,
            "degradation_mode": self.degradation_mode,
            "disclosure": self.disclosure,
        }


def build_provider_capability_manifest(
    *,
    provider_status: Dict[str, bool] | None = None,
) -> Dict[str, Dict[str, Any]]:
    status = dict(provider_status or {})

    manifests = [
        ProviderCapabilityManifest(
            provider="local",
            default_model="gemma",
            configured=bool(status.get("local", True)),
            capabilities=[
                "drafting",
                "rewrite",
                "summarization",
                "analysis",
                "classification",
                "planning",
            ],
            supports_long_running_sessions=True,
            supports_checkpoint_resume=True,
            supports_sandboxed_execution=True,
            supports_outcome_evaluation=False,
            supports_memory_dreaming=True,
            supports_multi_agent_orchestration=False,
            supports_mcp_private_connectors=False,
            max_tokens=8192,
            max_cost_per_task=0.0,
            runtime_limits={
                "network": "local_only",
                "external_writes": "blocked",
                "requires_human_review_for_business_state": True,
            },
            fallback_provider="openai",
            degradation_mode="local_first_then_cloud_if_allowed",
            disclosure="Local model runtime; safe for draft and analysis tasks, not autonomous business mutation.",
        ),
        ProviderCapabilityManifest(
            provider="openai",
            default_model="gpt-4.1-mini",
            configured=bool(status.get("openai", False)),
            capabilities=[
                "drafting",
                "rewrite",
                "summarization",
                "analysis",
                "reasoning",
                "planning",
                "classification",
            ],
            supports_long_running_sessions=False,
            supports_checkpoint_resume=False,
            supports_sandboxed_execution=False,
            supports_outcome_evaluation=True,
            supports_memory_dreaming=False,
            supports_multi_agent_orchestration=True,
            supports_mcp_private_connectors=False,
            max_tokens=128000,
            max_cost_per_task=5.0,
            runtime_limits={
                "network": "cloud",
                "external_writes": "approval_required",
                "requires_human_review_for_business_state": True,
            },
            fallback_provider="anthropic",
            degradation_mode="fallback_to_anthropic_or_local",
            disclosure="Cloud model provider; useful for high quality drafting, reasoning and planning.",
        ),
        ProviderCapabilityManifest(
            provider="anthropic",
            default_model="claude-sonnet-4-20250514",
            configured=bool(status.get("anthropic", False)),
            capabilities=[
                "drafting",
                "rewrite",
                "summarization",
                "analysis",
                "reasoning",
                "planning",
                "classification",
            ],
            enhanced_mode=True,
            supports_long_running_sessions=True,
            supports_checkpoint_resume=True,
            supports_sandboxed_execution=False,
            supports_outcome_evaluation=True,
            supports_memory_dreaming=False,
            supports_multi_agent_orchestration=True,
            supports_mcp_private_connectors=False,
            max_tokens=200000,
            max_cost_per_task=8.0,
            runtime_limits={
                "network": "cloud",
                "external_writes": "approval_required",
                "requires_human_review_for_business_state": True,
            },
            fallback_provider="openai",
            degradation_mode="fallback_to_openai_or_local",
            disclosure="Cloud reasoning provider; enhanced mode available for long-running planning/review tasks.",
        ),
    ]

    return {manifest.provider: manifest.to_dict() for manifest in manifests}


def provider_manifest_for_ui(provider_status: Dict[str, bool] | None = None) -> Dict[str, Any]:
    manifest = build_provider_capability_manifest(provider_status=provider_status)
    return {
        "schema_version": PROVIDER_CAPABILITY_MANIFEST_SCHEMA_VERSION,
        "trace_type": "provider_capability_manifest",
        "providers": manifest,
        "safe_defaults": {
            "external_writes_require_approval": True,
            "business_state_mutations_require_human_review": True,
            "local_provider_does_not_grant_permission": True,
            "provider_disclosure_required_in_ui": True,
        },
    }
