from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from backend.modules.aion_agents.contracts.agent_definition import AgentDefinition
from backend.modules.aion_agents.contracts.approval_request import ApprovalRequest
from backend.modules.aion_agents.contracts.workflow_definition import (
    WorkflowDefinition,
    WorkflowStepDefinition,
)
from backend.modules.aion_agents.contracts.workflow_run import (
    WorkflowRun,
    WorkflowStepRun,
)
from backend.modules.aion_agents.runtime.approval_request_repository import (
    ApprovalRequestRepository,
)
from backend.modules.aion_agents.runtime.workflow_run_repository import (
    WorkflowRunRepository,
)
from backend.modules.aion_business.contracts.skills import SkillRunRequest
from backend.modules.aion_business.runtime.image_generation_service import (
    ImageGenerationService,
)
from backend.modules.aion_business.runtime.local_asset_store import LocalAssetStore
from backend.modules.aion_business.skills.draft_content import DraftContentSkill


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class WorkflowExecutionRuntime:
    """
    Local workflow execution runtime.

    Supports:
    - create run
    - start run
    - execute until approval or completion
    - resolve approval
    - resume run
    - cancel run
    - marketing copy/image generation using full Brand Foundation snapshot
    """

    def __init__(
        self,
        *,
        workflow_definition_repository: Any | None = None,
        workflow_run_repository: Optional[WorkflowRunRepository] = None,
        approval_request_repository: Optional[ApprovalRequestRepository] = None,
    ) -> None:
        self.workflow_definition_repository = workflow_definition_repository
        self.workflow_run_repository = workflow_run_repository or WorkflowRunRepository()
        self.approval_request_repository = (
            approval_request_repository or ApprovalRequestRepository()
        )
        self.draft_content_skill = DraftContentSkill()
        self.local_asset_store = LocalAssetStore()

        self.image_generation_service = ImageGenerationService(
            base_dir=Path(".runtime") / "local_node" / "generated_images",
            asset_store=self.local_asset_store,
        )

    def _get_workflow_id(self, workflow: WorkflowDefinition) -> str:
        return str(
            getattr(workflow, "workflow_id", None)
            or getattr(workflow, "id", None)
            or ""
        )

    def _get_agent_id(self, agent: Optional[AgentDefinition]) -> Optional[str]:
        if agent is None:
            return None
        return getattr(agent, "agent_id", None) or getattr(agent, "id", None)

    def _step_id(self, step: WorkflowStepDefinition) -> str:
        return str(
            getattr(step, "id", None)
            or getattr(step, "step_id", None)
            or ""
        )

    def _step_name(self, step: WorkflowStepDefinition) -> str:
        return str(getattr(step, "name", None) or self._step_id(step) or "unnamed_step")

    def _step_kind(self, step: WorkflowStepDefinition) -> str:
        return str(
            getattr(step, "kind", None)
            or getattr(step, "step_kind", None)
            or getattr(step, "step_type", None)
            or ""
        )

    def _step_config(self, step: WorkflowStepDefinition) -> Dict[str, Any]:
        config = getattr(step, "config", None)
        return dict(config or {})

    def _step_requires_approval(self, step: WorkflowStepDefinition) -> bool:
        if bool(getattr(step, "requires_approval", False)):
            return True

        kind = self._step_kind(step)
        if kind in {"approval", "approval_checkpoint"}:
            return True

        return False

    def _step_next_id(self, step: WorkflowStepDefinition) -> Optional[str]:
        return (
            getattr(step, "next_step_id", None)
            or getattr(step, "on_success_step_id", None)
            or getattr(step, "next_step", None)
        )

    def _safe_agent_id(self, run: WorkflowRun, workflow: WorkflowDefinition) -> str:
        return str(
            run.agent_id
            or getattr(workflow, "agent_id", None)
            or "agent_marketing_operator_v1"
        )

    @staticmethod
    def _as_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]

        if isinstance(value, str):
            parts = (
                value.replace("•", "\n")
                .replace("·", "\n")
                .replace("|", "\n")
                .replace(",", "\n")
                .splitlines()
            )
            return [part.strip() for part in parts if part.strip()]

        return []

    @staticmethod
    def _first_string(*values: Any) -> str:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
            if value is not None and not isinstance(value, (dict, list)):
                raw = str(value).strip()
                if raw:
                    return raw
        return ""

    @staticmethod
    def _first_defined(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    def _get_brand_foundation(self, run: WorkflowRun) -> Dict[str, Any]:
        input_payload = dict(run.input_payload or {})
        context = dict(run.context or {})

        raw = (
            input_payload.get("brand_foundation_snapshot")
            or input_payload.get("brandFoundationState")
            or input_payload.get("brand_foundation")
            or context.get("brand_foundation_snapshot")
            or context.get("brandFoundationState")
            or context.get("brand_foundation")
            or {}
        )

        return dict(raw) if isinstance(raw, dict) else {}

    def _get_brand_map(self, run: WorkflowRun) -> Dict[str, Any]:
        input_payload = dict(run.input_payload or {})
        context = dict(run.context or {})
        brand_foundation = self._get_brand_foundation(run)

        raw = (
            input_payload.get("brand_map")
            or input_payload.get("brandMap")
            or context.get("brand_map")
            or context.get("brandMap")
            or brand_foundation.get("brand_map")
            or brand_foundation.get("brandMap")
            or brand_foundation.get("brand_intelligence_map")
            or brand_foundation.get("brandIntelligenceMap")
            or {}
        )

        return dict(raw) if isinstance(raw, dict) else {}

    def _get_nested_brand_section(
        self,
        brand_map: Dict[str, Any],
        *keys: str,
    ) -> Dict[str, Any]:
        for key in keys:
            value = brand_map.get(key)
            if isinstance(value, dict):
                return dict(value)
        return {}

    def _get_platform_strategy(
        self,
        *,
        marketing_strategy: Dict[str, Any],
        brand_foundation: Dict[str, Any],
        brand_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        section = self._get_nested_brand_section(
            brand_map,
            "platformStrategy",
            "platform_strategy",
            "channelStrategy",
            "channel_strategy",
        )

        return {
            **section,
            "channels": self._string_list(
                self._first_defined(
                    marketing_strategy.get("channels"),
                    brand_foundation.get("channels"),
                    section.get("channels"),
                    [],
                )
            ),
            "hashtags": self._string_list(
                self._first_defined(
                    marketing_strategy.get("hashtags"),
                    brand_foundation.get("hashtags"),
                    section.get("hashtags"),
                    [],
                )
            ),
            "keywords": self._string_list(
                self._first_defined(
                    marketing_strategy.get("keywords"),
                    brand_foundation.get("keywords"),
                    section.get("keywords"),
                    [],
                )
            ),
            "posting_rules": self._string_list(
                self._first_defined(
                    section.get("posting_rules"),
                    section.get("postingRules"),
                    section.get("rules"),
                    [],
                )
            ),
            "platform_notes": self._string_list(
                self._first_defined(
                    section.get("platform_notes"),
                    section.get("platformNotes"),
                    section.get("notes"),
                    [],
                )
            ),
        }

    def _get_creative_system(self, brand_map: Dict[str, Any]) -> Dict[str, Any]:
        return self._get_nested_brand_section(
            brand_map,
            "creativeSystem",
            "creative_system",
            "creativeDirection",
            "creative_direction",
        )

    def _get_visual_identity(self, brand_map: Dict[str, Any]) -> Dict[str, Any]:
        return self._get_nested_brand_section(
            brand_map,
            "visualIdentity",
            "visual_identity",
            "designSystem",
            "design_system",
        )

    def _get_audience_objective(
        self,
        *,
        marketing_strategy: Dict[str, Any],
        brand_foundation: Dict[str, Any],
        brand_map: Dict[str, Any],
    ) -> Dict[str, Any]:
        audience = self._get_nested_brand_section(
            brand_map,
            "audience",
            "audienceStrategy",
            "audience_strategy",
        )
        positioning = self._get_nested_brand_section(
            brand_map,
            "positioning",
            "brandPositioning",
            "brand_positioning",
        )
        campaign = self._get_nested_brand_section(
            brand_map,
            "campaign",
            "campaignContext",
            "campaign_context",
        )

        return {
            "objective": self._first_string(
                marketing_strategy.get("objective"),
                brand_foundation.get("objective"),
                positioning.get("objective"),
                campaign.get("objective"),
            ),
            "funnel_goal": self._first_string(
                marketing_strategy.get("funnel_goal"),
                marketing_strategy.get("funnelGoal"),
                brand_foundation.get("funnel_goal"),
                brand_foundation.get("funnelGoal"),
                campaign.get("funnel_goal"),
                campaign.get("funnelGoal"),
            ),
            "target_audience": self._first_string(
                marketing_strategy.get("target_audience"),
                marketing_strategy.get("targetAudience"),
                brand_foundation.get("target_audience"),
                brand_foundation.get("targetAudience"),
                audience.get("target_audience"),
                audience.get("targetAudience"),
                audience.get("primary"),
            ),
            "persona": self._first_string(
                marketing_strategy.get("persona"),
                brand_foundation.get("persona"),
                audience.get("persona"),
                audience.get("buyer_persona"),
                audience.get("buyerPersona"),
            ),
            "offer": self._first_string(
                marketing_strategy.get("offer"),
                brand_foundation.get("offer"),
                positioning.get("offer"),
                campaign.get("offer"),
            ),
            "audience_pain_points": self._string_list(
                audience.get("pain_points") or audience.get("painPoints") or []
            ),
            "audience_desires": self._string_list(
                audience.get("desires") or audience.get("motivations") or []
            ),
            "positioning": positioning,
            "campaign": campaign,
            "audience": audience,
        }

    def _get_rule_context(
        self,
        *,
        marketing_strategy: Dict[str, Any],
        brand_foundation: Dict[str, Any],
        brand_map: Dict[str, Any],
        department_notes: Dict[str, Any],
    ) -> Dict[str, list[str]]:
        rules = self._get_nested_brand_section(
            brand_map,
            "rules",
            "constraints",
            "brandRules",
            "brand_rules",
        )
        voice = self._get_nested_brand_section(
            brand_map,
            "voice",
            "tone",
            "brandVoice",
            "brand_voice",
        )

        return {
            "hard_rules": self._string_list(
                self._first_defined(
                    marketing_strategy.get("hard_rules"),
                    marketing_strategy.get("hardRules"),
                    department_notes.get("hard_rules"),
                    department_notes.get("hardRules"),
                    brand_foundation.get("hard_rules"),
                    brand_foundation.get("hardRules"),
                    rules.get("hard_rules"),
                    rules.get("hardRules"),
                    [],
                )
            ),
            "guidance_notes": self._string_list(
                self._first_defined(
                    marketing_strategy.get("guidance_notes"),
                    marketing_strategy.get("guidanceNotes"),
                    department_notes.get("guidance_notes"),
                    department_notes.get("guidanceNotes"),
                    brand_foundation.get("guidance_notes"),
                    brand_foundation.get("guidanceNotes"),
                    rules.get("guidance_notes"),
                    rules.get("guidanceNotes"),
                    [],
                )
            ),
            "campaign_notes": self._string_list(
                self._first_defined(
                    marketing_strategy.get("campaign_notes"),
                    marketing_strategy.get("campaignNotes"),
                    department_notes.get("campaign_notes"),
                    department_notes.get("campaignNotes"),
                    brand_foundation.get("campaign_notes"),
                    brand_foundation.get("campaignNotes"),
                    [],
                )
            ),
            "voice_tone": self._string_list(
                self._first_defined(
                    voice.get("tone"),
                    voice.get("tone_words"),
                    voice.get("toneWords"),
                    voice.get("style"),
                    [],
                )
            ),
            "avoid": self._string_list(
                self._first_defined(
                    rules.get("avoid"),
                    rules.get("donts"),
                    voice.get("avoid"),
                    [],
                )
            ),
        }

    def _build_brand_prompt_block(
        self,
        *,
        marketing_strategy: Dict[str, Any],
        brand_foundation: Dict[str, Any],
        brand_map: Dict[str, Any],
        department_notes: Dict[str, Any],
    ) -> str:
        platform_strategy = self._get_platform_strategy(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
        )
        audience_objective = self._get_audience_objective(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
        )
        creative_system = self._get_creative_system(brand_map)
        visual_identity = self._get_visual_identity(brand_map)
        rules = self._get_rule_context(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
            department_notes=department_notes,
        )

        lines: list[str] = ["Brand foundation context:"]

        if audience_objective.get("objective"):
            lines.append(f"- Objective: {audience_objective['objective']}")
        if audience_objective.get("funnel_goal"):
            lines.append(f"- Funnel goal: {audience_objective['funnel_goal']}")
        if audience_objective.get("target_audience"):
            lines.append(f"- Target audience: {audience_objective['target_audience']}")
        if audience_objective.get("persona"):
            lines.append(f"- Persona: {audience_objective['persona']}")
        if audience_objective.get("offer"):
            lines.append(f"- Offer: {audience_objective['offer']}")

        if audience_objective.get("audience_pain_points"):
            lines.append(
                "- Audience pain points: "
                + "; ".join(audience_objective["audience_pain_points"])
            )
        if audience_objective.get("audience_desires"):
            lines.append(
                "- Audience desires: "
                + "; ".join(audience_objective["audience_desires"])
            )

        if platform_strategy.get("channels"):
            lines.append("- Channels: " + ", ".join(platform_strategy["channels"]))
        if platform_strategy.get("hashtags"):
            lines.append("- Hashtags: " + ", ".join(platform_strategy["hashtags"]))
        if platform_strategy.get("keywords"):
            lines.append("- Keywords: " + ", ".join(platform_strategy["keywords"]))
        if platform_strategy.get("posting_rules"):
            lines.append(
                "- Platform posting rules: "
                + "; ".join(platform_strategy["posting_rules"])
            )
        if platform_strategy.get("platform_notes"):
            lines.append(
                "- Platform notes: "
                + "; ".join(platform_strategy["platform_notes"])
            )

        creative_direction = self._first_string(
            creative_system.get("creative_direction"),
            creative_system.get("creativeDirection"),
            creative_system.get("direction"),
            creative_system.get("style_direction"),
            creative_system.get("styleDirection"),
        )
        if creative_direction:
            lines.append(f"- Creative direction: {creative_direction}")

        image_style = self._first_string(
            creative_system.get("image_style"),
            creative_system.get("imageStyle"),
            creative_system.get("visual_style"),
            creative_system.get("visualStyle"),
        )
        if image_style:
            lines.append(f"- Image style: {image_style}")

        layout_rules = self._string_list(
            creative_system.get("layout_rules")
            or creative_system.get("layoutRules")
            or creative_system.get("layout")
            or []
        )
        if layout_rules:
            lines.append("- Layout rules: " + "; ".join(layout_rules))

        font_rules = self._string_list(
            visual_identity.get("font_rules")
            or visual_identity.get("fontRules")
            or visual_identity.get("fonts")
            or visual_identity.get("typography")
            or []
        )
        if font_rules:
            lines.append("- Font rules: " + "; ".join(font_rules))

        colour_rules = self._string_list(
            visual_identity.get("colour_rules")
            or visual_identity.get("color_rules")
            or visual_identity.get("colourRules")
            or visual_identity.get("colorRules")
            or visual_identity.get("colours")
            or visual_identity.get("colors")
            or []
        )
        if colour_rules:
            lines.append("- Colour rules: " + "; ".join(colour_rules))

        if rules.get("voice_tone"):
            lines.append("- Voice / tone: " + "; ".join(rules["voice_tone"]))
        if rules.get("hard_rules"):
            lines.append("- Hard rules: " + "; ".join(rules["hard_rules"]))
        if rules.get("guidance_notes"):
            lines.append("- Guidance notes: " + "; ".join(rules["guidance_notes"]))
        if rules.get("campaign_notes"):
            lines.append("- Campaign notes: " + "; ".join(rules["campaign_notes"]))
        if rules.get("avoid"):
            lines.append("- Avoid: " + "; ".join(rules["avoid"]))

        return "\n".join(lines).strip()

    def _safe_objective(
        self,
        *,
        workflow: WorkflowDefinition,
        brief: str,
        marketing_strategy: Dict[str, Any],
        brand_foundation: Dict[str, Any],
    ) -> str:
        brand_map = (
            brand_foundation.get("brand_map")
            or brand_foundation.get("brandMap")
            or {}
        )
        audience_objective = self._get_audience_objective(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map if isinstance(brand_map, dict) else {},
        )

        return str(
            audience_objective.get("objective")
            or marketing_strategy.get("objective")
            or brand_foundation.get("objective")
            or brief
            or workflow.name
            or "draft_content"
        )

    def _resolve_model_preferences(
        self,
        *,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        marketing_strategy: Dict[str, Any],
        brand_foundation: Dict[str, Any],
        step_config: Dict[str, Any],
    ) -> Dict[str, Optional[str]]:
        input_payload = dict(run.input_payload or {})
        context = dict(run.context or {})

        selected_provider = (
            step_config.get("selected_provider")
            or step_config.get("provider")
            or marketing_strategy.get("selected_provider")
            or brand_foundation.get("selected_provider")
            or input_payload.get("selected_provider")
            or context.get("selected_provider")
            or (
                (input_payload.get("model_selection") or {}).get("provider")
                if isinstance(input_payload.get("model_selection"), dict)
                else None
            )
            or (
                (context.get("model_selection") or {}).get("provider")
                if isinstance(context.get("model_selection"), dict)
                else None
            )
        )

        selected_model = (
            step_config.get("selected_model")
            or step_config.get("preferred_model")
            or marketing_strategy.get("selected_model")
            or brand_foundation.get("selected_model")
            or input_payload.get("selected_model")
            or context.get("selected_model")
            or (
                (input_payload.get("model_selection") or {}).get("model")
                if isinstance(input_payload.get("model_selection"), dict)
                else None
            )
            or (
                (context.get("model_selection") or {}).get("model")
                if isinstance(context.get("model_selection"), dict)
                else None
            )
        )

        selected_policy = (
            step_config.get("model_policy_ref")
            or marketing_strategy.get("model_policy_ref")
            or brand_foundation.get("model_policy_ref")
            or input_payload.get("model_policy_ref")
            or context.get("model_policy_ref")
            or (
                (input_payload.get("model_selection") or {}).get("policy_ref")
                if isinstance(input_payload.get("model_selection"), dict)
                else None
            )
            or (
                (context.get("model_selection") or {}).get("policy_ref")
                if isinstance(context.get("model_selection"), dict)
                else None
            )
        )

        return {
            "selected_provider": str(selected_provider) if selected_provider else None,
            "selected_model": str(selected_model) if selected_model else None,
            "model_policy_ref": str(selected_policy) if selected_policy else None,
        }

    def _get_creative_assets(self, run: WorkflowRun) -> list[Dict[str, Any]]:
        input_payload = dict(run.input_payload or {})
        context = dict(run.context or {})

        raw_assets = (
            input_payload.get("creative_assets")
            or context.get("creative_assets")
            or input_payload.get("assets")
            or context.get("assets")
            or []
        )

        assets: list[Dict[str, Any]] = []

        for index, item in enumerate(self._as_list(raw_assets)):
            if not isinstance(item, dict):
                continue

            asset_type = str(
                item.get("type")
                or item.get("asset_type")
                or item.get("intent")
                or "reference"
            ).strip() or "reference"

            asset_id = str(item.get("id") or f"asset_{index + 1}")
            label = str(item.get("label") or item.get("name") or asset_id)
            url = item.get("url") or item.get("asset_url") or item.get("image_url")
            file_path = item.get("file_path") or item.get("path")
            notes = item.get("notes") or item.get("usage_notes") or ""

            assets.append(
                {
                    "id": asset_id,
                    "type": asset_type,
                    "label": label,
                    "url": url,
                    "file_path": file_path,
                    "mime_type": item.get("mime_type"),
                    "size_bytes": item.get("size_bytes"),
                    "notes": notes,
                }
            )

        return assets

    def _get_creative_direction(self, run: WorkflowRun) -> Dict[str, Any]:
        input_payload = dict(run.input_payload or {})
        context = dict(run.context or {})

        raw = (
            input_payload.get("creative_direction")
            or context.get("creative_direction")
            or {}
        )

        if not isinstance(raw, dict):
            raw = {}

        return {
            "asset_intent": raw.get("asset_intent")
            or raw.get("assetIntent")
            or raw.get("intent"),
            "product_name": raw.get("product_name")
            or raw.get("productName")
            or raw.get("subject_name")
            or raw.get("subjectName"),
            "offer_price": raw.get("offer_price")
            or raw.get("offerPrice")
            or raw.get("price"),
            "offer_details": raw.get("offer_details")
            or raw.get("offerDetails")
            or raw.get("details"),
            "usage_notes": raw.get("usage_notes")
            or raw.get("usageNotes")
            or raw.get("image_usage_notes")
            or raw.get("imageUsageNotes"),
            "style_direction": raw.get("style_direction")
            or raw.get("styleDirection"),
            "creative_direction": raw.get("creative_direction")
            or raw.get("creativeDirection")
            or raw.get("direction"),
        }

    def _build_creative_asset_prompt_block(self, run: WorkflowRun) -> str:
        creative_assets = self._get_creative_assets(run)
        creative_direction = self._get_creative_direction(run)

        lines: list[str] = []

        if creative_direction:
            lines.append("Creative direction:")
            if creative_direction.get("asset_intent"):
                lines.append(f"- Asset intent: {creative_direction.get('asset_intent')}")
            if creative_direction.get("product_name"):
                lines.append(f"- Product / subject: {creative_direction.get('product_name')}")
            if creative_direction.get("offer_price"):
                lines.append(f"- Offer price: {creative_direction.get('offer_price')}")
            if creative_direction.get("offer_details"):
                lines.append(f"- Offer details: {creative_direction.get('offer_details')}")
            if creative_direction.get("creative_direction"):
                lines.append(f"- Direction: {creative_direction.get('creative_direction')}")
            if creative_direction.get("usage_notes"):
                lines.append(f"- Image usage notes: {creative_direction.get('usage_notes')}")
            if creative_direction.get("style_direction"):
                lines.append(f"- Style direction: {creative_direction.get('style_direction')}")

        if creative_assets:
            lines.append("")
            lines.append("Creative assets supplied by the user:")
            for asset in creative_assets:
                label = asset.get("label") or asset.get("id") or "Asset"
                asset_type = asset.get("type") or "reference"
                url = asset.get("url") or asset.get("file_path") or ""
                notes = asset.get("notes") or ""
                lines.append(f"- {label} [{asset_type}]")
                if url:
                    lines.append(f"  Source: {url}")
                if notes:
                    lines.append(f"  Notes: {notes}")

            lines.append("")
            lines.append("Use these assets as creative inputs. Do not ignore them.")
            lines.append("If a product asset is supplied, build the carousel around that product.")
            lines.append("If logo/headshot/reference/background assets are supplied, respect the user's usage notes.")

        return "\n".join(lines).strip()

    def create_run(
        self,
        *,
        workflow: WorkflowDefinition,
        agent: Optional[AgentDefinition] = None,
        trigger_id: Optional[str] = None,
        trigger_event_type: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        now = _utc_now_iso()
        first_step = workflow.get_first_step()
        workflow_id = self._get_workflow_id(workflow)
        agent_id = (
            self._get_agent_id(agent)
            or getattr(workflow, "agent_id", None)
            or "agent_marketing_operator_v1"
        )

        merged_context = dict(context or {})
        merged_input = dict(input_payload or {})

        for key in (
            "brief",
            "marketing_strategy",
            "brand_foundation_snapshot",
            "brandFoundationState",
            "brand_foundation",
            "brand_map",
            "brandMap",
            "department_notes",
            "selected_provider",
            "selected_model",
            "model_policy_ref",
            "model_selection",
            "selected_image_provider",
            "selected_image_model",
            "visual_assets",
            "creative_assets",
            "creative_direction",
            "logo_url",
            "headshot_url",
            "product_image_urls",
            "reference_image_urls",
        ):
            if key in merged_input and key not in merged_context:
                merged_context[key] = merged_input[key]

        run = WorkflowRun(
            id=f"run_{uuid4().hex[:16]}",
            workspace_id=workflow.workspace_id,
            workflow_id=workflow_id,
            workflow_version=workflow.version,
            workflow_name=workflow.name,
            agent_id=agent_id,
            department_key=(
                getattr(agent, "department_key", None) if agent else None
            ) or workflow.department_key,
            trigger_id=trigger_id,
            trigger_event_type=trigger_event_type,
            status="queued",
            current_step_id=self._step_id(first_step) if first_step else None,
            input_payload=merged_input,
            context=merged_context,
            result_payload={},
            created_at=now,
            updated_at=now,
        )
        return self.workflow_run_repository.save(run)

    def start_run(self, workflow: WorkflowDefinition, run_id: str) -> WorkflowRun:
        run = self.workflow_run_repository.load(workflow.workspace_id, run_id)
        if run.status not in {"queued", "blocked"}:
            return run

        now = _utc_now_iso()
        run.status = "running"
        run.started_at = run.started_at or now
        run.updated_at = now
        run = self.workflow_run_repository.save(run)
        return self.execute_next(workflow, run.id)

    def launch_workflow(
        self,
        *,
        workflow: WorkflowDefinition,
        agent: Optional[AgentDefinition] = None,
        trigger_id: Optional[str] = None,
        trigger_event_type: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        run = self.create_run(
            workflow=workflow,
            agent=agent,
            trigger_id=trigger_id,
            trigger_event_type=trigger_event_type,
            input_payload=input_payload,
            context=context,
        )
        return self.start_run(workflow, run.id)

    def execute_next(self, workflow: WorkflowDefinition, run_id: str) -> WorkflowRun:
        run = self.workflow_run_repository.load(workflow.workspace_id, run_id)

        if run.status in {"completed", "failed", "cancelled"}:
            return run

        if not run.current_step_id:
            run.status = "completed"
            run.completed_at = _utc_now_iso()
            run.updated_at = run.completed_at
            run.result_payload["post_package"] = self._build_marketing_post_package(run)
            return self.workflow_run_repository.save(run)

        step = workflow.get_step(run.current_step_id)
        if step is None:
            run.status = "failed"
            run.error_message = f"Step not found: {run.current_step_id}"
            run.updated_at = _utc_now_iso()
            return self.workflow_run_repository.save(run)

        if self._should_pause_for_approval(workflow, step):
            return self._create_approval_and_pause(run=run, workflow=workflow, step=step)

        return self._execute_step(run=run, workflow=workflow, step=step)

    def _should_pause_for_approval(
        self,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
    ) -> bool:
        if self._step_requires_approval(step):
            return True

        if workflow.execution_mode in {"draft_with_approval", "draft_and_approval"} and self._step_kind(step) in {
            "send_email",
        }:
            return True

        return False

    def _create_approval_and_pause(
        self,
        *,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
    ) -> WorkflowRun:
        now = _utc_now_iso()
        step_id = self._step_id(step)
        step_name = self._step_name(step)
        step_kind = self._step_kind(step)

        approval_packet = self._build_marketing_approval_packet(run, workflow, step)
        run.context["approval_packet"] = approval_packet
        run.result_payload["approval_packet"] = approval_packet

        existing_post_package = (
            run.context.get("post_package")
            if isinstance(run.context.get("post_package"), dict)
            else None
        ) or self._build_marketing_post_package(run)

        existing_post_package["approval_packet"] = approval_packet
        run.context["post_package"] = existing_post_package
        run.result_payload["post_package"] = existing_post_package

        approval = ApprovalRequest(
            id=f"approval_{uuid4().hex[:16]}",
            workspace_id=run.workspace_id,
            workflow_run_id=run.id,
            workflow_id=run.workflow_id,
            agent_id=run.agent_id,
            department_key=run.department_key,
            title=f"Approval required: {workflow.name}",
            summary=f"Step '{step_name}' is waiting for approval.",
            approval_class="draft_review",
            requested_action={
                "step_id": step_id,
                "step_kind": step_kind,
                "step_name": step_name,
            },
            context={
                "workflow_name": workflow.name,
                "run_id": run.id,
                "approval_packet": approval_packet,
            },
            requested_at=now,
        )
        self.approval_request_repository.save(approval)

        run.status = "waiting_approval"
        run.approval_request_id = approval.id
        run.updated_at = now

        run.step_runs.append(
            WorkflowStepRun(
                step_id=step_id,
                step_name=step_name,
                step_kind=step_kind,
                status="waiting_approval",
                input_payload={
                    "approval_packet": approval_packet,
                },
                output_payload={
                    "approval_request_id": approval.id,
                    "approval_packet": approval_packet,
                },
                started_at=now,
            )
        )
        return self.workflow_run_repository.save(run)

    def _execute_step(
        self,
        *,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
    ) -> WorkflowRun:
        now = _utc_now_iso()
        step_id = self._step_id(step)
        step_name = self._step_name(step)
        step_kind = self._step_kind(step)
        step_config = self._step_config(step)

        step_run = WorkflowStepRun(
            step_id=step_id,
            step_name=step_name,
            step_kind=step_kind,
            status="running",
            input_payload={
                "config": step_config,
                "context": dict(run.context or {}),
                "input_payload": dict(run.input_payload or {}),
            },
            started_at=now,
        )

        try:
            output_payload = self._simulate_step_output(
                run=run,
                workflow=workflow,
                step=step,
            )

            if step_kind in {"draft_content", "llm_task", "post_social"}:
                post_package = self._build_marketing_post_package(run)

                if step_kind == "post_social":
                    publish_result = (
                        output_payload.get("publish_result")
                        if isinstance(output_payload, dict)
                        else None
                    )
                    generated_image = (
                        publish_result.get("generated_image")
                        if isinstance(publish_result, dict)
                        else None
                    )
                    generated_images = (
                        publish_result.get("generated_images")
                        if isinstance(publish_result, dict)
                        else None
                    )
                    carousel_cards = (
                        publish_result.get("carousel_cards")
                        if isinstance(publish_result, dict)
                        else None
                    )

                    if generated_image:
                        post_package["generated_image"] = generated_image

                    if generated_images:
                        post_package["generated_images"] = generated_images

                    if carousel_cards:
                        post_package["carousel_cards"] = carousel_cards

                    if generated_image:
                        image_generation = dict(post_package.get("image_generation") or {})
                        image_generation.update(
                            {
                                "provider": generated_image.get("provider"),
                                "model": generated_image.get("model"),
                                "status": generated_image.get("status", "completed"),
                                "asset_url": (
                                    generated_image.get("asset_url")
                                    or generated_image.get("url")
                                    or generated_image.get("file_path")
                                ),
                                "asset_id": (
                                    generated_image.get("asset_id")
                                    or generated_image.get("file_path")
                                ),
                                "error": generated_image.get("error"),
                            }
                        )
                        post_package["image_generation"] = image_generation

                    if publish_result:
                        post_package["publish_result"] = publish_result
                        run.context["publish_result"] = publish_result
                        run.result_payload["publish_result"] = publish_result

                run.context["post_package"] = post_package
                run.result_payload["post_package"] = post_package

            step_run.status = "completed"
            step_run.output_payload = output_payload
            step_run.completed_at = _utc_now_iso()

            run.step_runs.append(step_run)
            run.result_payload[step_id] = output_payload

            next_step_id = self._step_next_id(step)
            run.current_step_id = next_step_id

            if step_kind == "complete" or not next_step_id:
                run.status = "completed"
                run.completed_at = _utc_now_iso()

                final_post_package = self._build_marketing_post_package(run)

                if step_kind == "post_social":
                    publish_result = (
                        output_payload.get("publish_result")
                        if isinstance(output_payload, dict)
                        else None
                    )
                    generated_image = (
                        publish_result.get("generated_image")
                        if isinstance(publish_result, dict)
                        else None
                    )
                    generated_images = (
                        publish_result.get("generated_images")
                        if isinstance(publish_result, dict)
                        else None
                    )
                    carousel_cards = (
                        publish_result.get("carousel_cards")
                        if isinstance(publish_result, dict)
                        else None
                    )

                    if generated_image:
                        final_post_package["generated_image"] = generated_image

                    if generated_images:
                        final_post_package["generated_images"] = generated_images

                    if carousel_cards:
                        final_post_package["carousel_cards"] = carousel_cards

                    if generated_image:
                        image_generation = dict(
                            final_post_package.get("image_generation") or {}
                        )
                        image_generation.update(
                            {
                                "provider": generated_image.get("provider"),
                                "model": generated_image.get("model"),
                                "status": generated_image.get("status", "completed"),
                                "asset_url": (
                                    generated_image.get("asset_url")
                                    or generated_image.get("url")
                                    or generated_image.get("file_path")
                                ),
                                "asset_id": (
                                    generated_image.get("asset_id")
                                    or generated_image.get("file_path")
                                ),
                                "error": generated_image.get("error"),
                            }
                        )
                        final_post_package["image_generation"] = image_generation

                    if publish_result:
                        final_post_package["publish_result"] = publish_result
                        run.context["publish_result"] = publish_result
                        run.result_payload["publish_result"] = publish_result

                run.context["post_package"] = final_post_package
                run.result_payload["post_package"] = final_post_package
            else:
                run.status = "running"

            run.updated_at = _utc_now_iso()
            saved = self.workflow_run_repository.save(run)

            if saved.status == "running" and saved.current_step_id:
                return self.execute_next(workflow, saved.id)

            return saved

        except Exception as exc:
            step_run.status = "failed"
            step_run.error_message = f"{type(exc).__name__}: {exc}"
            step_run.completed_at = _utc_now_iso()
            run.step_runs.append(step_run)
            run.status = "failed"
            run.error_message = step_run.error_message
            run.updated_at = _utc_now_iso()
            return self.workflow_run_repository.save(run)

    def _build_marketing_approval_packet(
        self,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
    ) -> Dict[str, Any]:
        context = dict(run.context or {})
        result_payload = dict(run.result_payload or {})
        input_payload = dict(run.input_payload or {})

        marketing_strategy = dict(input_payload.get("marketing_strategy") or {})
        brand_foundation = self._get_brand_foundation(run)
        brand_map = self._get_brand_map(run)
        department_notes = dict(input_payload.get("department_notes") or {})

        creative_assets = self._get_creative_assets(run)
        creative_direction = self._get_creative_direction(run)
        platform_strategy = self._get_platform_strategy(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
        )
        audience_objective = self._get_audience_objective(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
        )
        creative_system = self._get_creative_system(brand_map)
        visual_identity = self._get_visual_identity(brand_map)
        rule_context = self._get_rule_context(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
            department_notes=department_notes,
        )

        model_preferences = self._resolve_model_preferences(
            run=run,
            workflow=workflow,
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            step_config=self._step_config(step),
        )

        draft_caption = (
            (result_payload.get("draft_caption") or {}).get("draft_caption")
            or context.get("draft_caption")
            or input_payload.get("brief")
            or ""
        )

        draft_carousel = (
            (result_payload.get("draft_carousel") or {}).get("draft_carousel")
            or context.get("draft_carousel")
            or []
        )

        return {
            "type": "marketing_approval_packet",
            "run_id": run.id,
            "workflow_id": run.workflow_id,
            "workflow_name": workflow.name,
            "department_key": run.department_key,
            "step_id": self._step_id(step),
            "step_name": self._step_name(step),
            "brief": input_payload.get("brief") or context.get("brief"),
            "draft_caption": draft_caption,
            "draft_carousel": draft_carousel,
            "channels": platform_strategy.get("channels") or [],
            "platform_strategy": platform_strategy,
            "audience_objective": audience_objective,
            "creative_system": creative_system,
            "visual_identity": visual_identity,
            "brand_foundation_snapshot": brand_foundation,
            "brand_map": brand_map,
            "brandMap": brand_map,
            "hard_rules": rule_context.get("hard_rules") or [],
            "guidance_notes": rule_context.get("guidance_notes") or [],
            "campaign_notes": rule_context.get("campaign_notes") or [],
            "voice_tone": rule_context.get("voice_tone") or [],
            "avoid": rule_context.get("avoid") or [],
            "creative_assets": creative_assets,
            "creative_direction": creative_direction,
            "selected_provider": model_preferences.get("selected_provider"),
            "selected_model": model_preferences.get("selected_model"),
            "status": "waiting_approval",
            "generated_at": _utc_now_iso(),
        }

    def _build_marketing_post_package(self, run: WorkflowRun) -> Dict[str, Any]:
        context = dict(run.context or {})
        result_payload = dict(run.result_payload or {})
        input_payload = dict(run.input_payload or {})

        marketing_strategy = dict(input_payload.get("marketing_strategy") or {})
        brand_foundation = self._get_brand_foundation(run)
        brand_map = self._get_brand_map(run)
        department_notes = dict(input_payload.get("department_notes") or {})

        platform_strategy = self._get_platform_strategy(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
        )
        audience_objective = self._get_audience_objective(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
        )
        creative_system = self._get_creative_system(brand_map)
        visual_identity = self._get_visual_identity(brand_map)
        rule_context = self._get_rule_context(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
            department_notes=department_notes,
        )

        creative_assets = self._get_creative_assets(run)
        creative_direction = self._get_creative_direction(run)
        creative_asset_prompt_block = self._build_creative_asset_prompt_block(run)
        brand_prompt_block = self._build_brand_prompt_block(
            marketing_strategy=marketing_strategy,
            brand_foundation=brand_foundation,
            brand_map=brand_map,
            department_notes=department_notes,
        )

        draft_caption = (
            (result_payload.get("draft_caption") or {}).get("draft_caption")
            or context.get("draft_caption")
            or ""
        )

        draft_carousel = (
            (result_payload.get("draft_carousel") or {}).get("draft_carousel")
            or context.get("draft_carousel")
            or []
        )

        channels = platform_strategy.get("channels") or []
        primary_channel = str(channels[0]) if channels else "general"
        primary_channel_slug = (
            primary_channel.strip().lower().replace(" ", "_").replace("-", "_")
            if primary_channel
            else "general"
        )

        hashtags = platform_strategy.get("hashtags") or []
        keywords = platform_strategy.get("keywords") or []

        brief = input_payload.get("brief") or context.get("brief")
        objective = audience_objective.get("objective") or brief or run.workflow_name
        funnel_goal = audience_objective.get("funnel_goal")
        target_audience = audience_objective.get("target_audience")
        persona = audience_objective.get("persona")
        offer = audience_objective.get("offer")

        selected_provider = (
            marketing_strategy.get("selected_provider")
            or brand_foundation.get("selected_provider")
            or input_payload.get("selected_provider")
            or context.get("selected_provider")
            or "openai"
        )
        selected_model = (
            marketing_strategy.get("selected_model")
            or brand_foundation.get("selected_model")
            or input_payload.get("selected_model")
            or context.get("selected_model")
            or None
        )

        image_provider = (
            marketing_strategy.get("selected_image_provider")
            or brand_foundation.get("selected_image_provider")
            or input_payload.get("selected_image_provider")
            or context.get("selected_image_provider")
            or "openai"
        )
        image_model = (
            marketing_strategy.get("selected_image_model")
            or brand_foundation.get("selected_image_model")
            or input_payload.get("selected_image_model")
            or context.get("selected_image_model")
            or "gpt-image-1"
        )

        hard_rules = rule_context.get("hard_rules") or []
        guidance_notes = rule_context.get("guidance_notes") or []
        campaign_notes = rule_context.get("campaign_notes") or []
        voice_tone = rule_context.get("voice_tone") or []
        avoid = rule_context.get("avoid") or []

        visual_assets = dict(
            input_payload.get("visual_assets")
            or context.get("visual_assets")
            or {}
        )

        for key in (
            "logo_url",
            "headshot_url",
            "product_image_urls",
            "reference_image_urls",
        ):
            if key in input_payload and key not in visual_assets:
                visual_assets[key] = input_payload[key]
            if key in context and key not in visual_assets:
                visual_assets[key] = context[key]

        grouped_assets: Dict[str, list[Dict[str, Any]]] = {}
        for asset in creative_assets:
            asset_type = str(asset.get("type") or "reference").strip() or "reference"
            grouped_assets.setdefault(asset_type, []).append(asset)

        visual_assets["creative_assets"] = creative_assets
        visual_assets["creative_direction"] = creative_direction
        visual_assets["assets_by_type"] = grouped_assets
        visual_assets["creative_system"] = creative_system
        visual_assets["visual_identity"] = visual_identity
        visual_assets["font_rules"] = self._string_list(
            visual_identity.get("font_rules")
            or visual_identity.get("fontRules")
            or visual_identity.get("fonts")
            or visual_identity.get("typography")
            or []
        )
        visual_assets["colour_rules"] = self._string_list(
            visual_identity.get("colour_rules")
            or visual_identity.get("color_rules")
            or visual_identity.get("colourRules")
            or visual_identity.get("colorRules")
            or visual_identity.get("colours")
            or visual_identity.get("colors")
            or []
        )

        image_prompt_parts = [
            "Create a clean, professional social media visual.",
            f"Brand/workflow: {run.workflow_name}.",
            f"Brief: {brief or run.workflow_name}.",
        ]

        if offer:
            image_prompt_parts.append(f"Offer: {offer}.")
        if target_audience:
            image_prompt_parts.append(f"Audience: {target_audience}.")
        if channels:
            image_prompt_parts.append(
                f"Primary channels: {', '.join(str(x) for x in channels)}."
            )
        if persona:
            image_prompt_parts.append(f"Persona: {persona}.")
        if objective:
            image_prompt_parts.append(f"Objective: {objective}.")
        if funnel_goal:
            image_prompt_parts.append(f"Funnel goal: {funnel_goal}.")

        if brand_prompt_block:
            image_prompt_parts.append(brand_prompt_block)
        if creative_asset_prompt_block:
            image_prompt_parts.append(creative_asset_prompt_block)

        existing_post_package = context.get("post_package")
        existing_generated_image = (
            existing_post_package.get("generated_image")
            if isinstance(existing_post_package, dict)
            else None
        )
        existing_generated_images = (
            existing_post_package.get("generated_images")
            if isinstance(existing_post_package, dict)
            else None
        )
        existing_carousel_cards = (
            existing_post_package.get("carousel_cards")
            if isinstance(existing_post_package, dict)
            else None
        )
        existing_publish_result = (
            existing_post_package.get("publish_result")
            if isinstance(existing_post_package, dict)
            else None
        )

        post_package = {
            "type": "marketing_post_package",
            "run_id": run.id,
            "workflow_id": run.workflow_id,
            "workflow_name": run.workflow_name,
            "workflow_version": run.workflow_version,
            "agent_id": run.agent_id,
            "department_key": run.department_key,
            "brief": brief,
            "objective": objective,
            "funnel_goal": funnel_goal,
            "target_audience": target_audience,
            "persona": persona,
            "offer": offer,
            "title": run.workflow_name,
            "caption": draft_caption,
            "body": draft_caption,
            "carousel": draft_carousel,
            "content_blocks": draft_carousel,
            "channels": channels,
            "primary_channel": primary_channel,
            "hashtags": hashtags,
            "keywords": keywords,
            "hard_rules": hard_rules,
            "guidance_notes": guidance_notes,
            "campaign_notes": campaign_notes,
            "voice_tone": voice_tone,
            "avoid": avoid,
            "platform_strategy": platform_strategy,
            "audience_objective": audience_objective,
            "creative_system": creative_system,
            "visual_identity": visual_identity,
            "brand_foundation_snapshot": brand_foundation,
            "brand_map": brand_map,
            "brandMap": brand_map,
            "scheduled_for": run.created_at,
            "visual_type": "carousel" if len(draft_carousel) > 1 else "text",
            "selected_provider": selected_provider,
            "selected_model": selected_model,
            "selected_image_provider": image_provider,
            "selected_image_model": image_model,
            "local_asset_root": "Tessaris",
            "local_asset_family": "marketing",
            "local_asset_collection": primary_channel_slug,
            "image_prompt": " ".join(part.strip() for part in image_prompt_parts if part),
            "visual_assets": visual_assets,
            "creative_assets": creative_assets,
            "creative_direction": creative_direction,
            "image_generation": {
                "provider": image_provider,
                "model": image_model,
                "status": "pending",
                "asset_url": None,
                "asset_id": None,
                "error": None,
            },
            "approval_packet": context.get("approval_packet"),
            "approval_decision": context.get("approval_decision"),
            "publish_result": context.get("publish_result"),
            "status": run.status,
            "generated_at": _utc_now_iso(),
        }

        if existing_generated_image:
            post_package["generated_image"] = existing_generated_image
            post_package["image_generation"] = {
                "provider": existing_generated_image.get("provider", image_provider),
                "model": existing_generated_image.get("model", image_model),
                "status": existing_generated_image.get("status", "completed"),
                "asset_url": (
                    existing_generated_image.get("asset_url")
                    or existing_generated_image.get("file_path")
                    or existing_generated_image.get("url")
                ),
                "asset_id": (
                    existing_generated_image.get("asset_id")
                    or existing_generated_image.get("file_path")
                ),
                "error": existing_generated_image.get("error"),
            }

        if existing_generated_images:
            post_package["generated_images"] = existing_generated_images

        if existing_carousel_cards:
            post_package["carousel_cards"] = existing_carousel_cards

        if existing_publish_result:
            post_package["publish_result"] = existing_publish_result

        return post_package

    def _generate_openai_marketing_image(
        self,
        *,
        prompt: str,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
    ) -> Dict[str, Any]:
        creative_assets = self._get_creative_assets(run)
        creative_direction = self._get_creative_direction(run)
        brand_foundation = self._get_brand_foundation(run)
        brand_map = self._get_brand_map(run)

        assets_by_type: Dict[str, list[Dict[str, Any]]] = {}
        for asset in creative_assets:
            if not isinstance(asset, dict):
                continue

            asset_type = str(
                asset.get("type")
                or asset.get("asset_type")
                or asset.get("intent")
                or "reference"
            ).strip().lower()

            if not asset_type:
                asset_type = "reference"

            assets_by_type.setdefault(asset_type, []).append(asset)

        visual_assets = {
            "creative_assets": creative_assets,
            "creative_direction": creative_direction,
            "assets_by_type": assets_by_type,
            "brand_foundation_snapshot": brand_foundation,
            "brand_map": brand_map,
        }

        creative_asset_prompt_block = self._build_creative_asset_prompt_block(run)
        brand_prompt_block = self._build_brand_prompt_block(
            marketing_strategy=dict(run.input_payload.get("marketing_strategy") or {}),
            brand_foundation=brand_foundation,
            brand_map=brand_map,
            department_notes=dict(run.input_payload.get("department_notes") or {}),
        )

        final_prompt = str(prompt or "").strip()

        for block in (brand_prompt_block, creative_asset_prompt_block):
            if block and block not in final_prompt:
                final_prompt = f"{final_prompt}\n\n{block}".strip()

        print("WORKFLOW IMAGE CALL FILE =", __file__)
        print("WORKFLOW IMAGE PROMPT =", repr(final_prompt))

        result = self.image_generation_service.generate_marketing_image(
            prompt=final_prompt,
            provider="openai",
            model="gpt-image-1",
            size="1024x1536",
            file_stem=f"{run.id}_{self._step_id(step)}",
            metadata={
                "workspace_id": run.workspace_id,
                "workflow_id": run.workflow_id,
                "workflow_run_id": run.id,
                "run_id": run.id,
                "step_id": self._step_id(step),
                "department_key": run.department_key,
                "primary_channel": "facebook",
                "channel": "facebook",
                "creative_assets_count": len(creative_assets),
                "creative_asset_types": sorted(assets_by_type.keys()),
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "brand_foundation_snapshot": brand_foundation,
                "brand_map": brand_map,
            },
            visual_assets=visual_assets,
        )

        if not result.get("ok"):
            raise RuntimeError(str(result.get("error") or "image_generation_failed"))

        return {
            "provider": result.get("provider"),
            "model": result.get("model"),
            "status": "completed",
            "url": (
                result.get("asset_url")
                or result.get("url")
                or result.get("file_path")
            ),
            "asset_url": result.get("asset_url") or result.get("url"),
            "asset_id": result.get("asset_id"),
            "file_path": result.get("file_path"),
            "mime_type": result.get("mime_type"),
            "creative_assets": creative_assets,
            "creative_direction": creative_direction,
            "assets_by_type": assets_by_type,
            "visual_assets": visual_assets,
            "brand_foundation_snapshot": brand_foundation,
            "brand_map": brand_map,
            "error": None,
        }

    def _generate_openai_marketing_carousel_cards(
        self,
        *,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
        post_package: Dict[str, Any],
    ) -> Dict[str, Any]:
        creative_assets = list(
            post_package.get("creative_assets")
            or self._get_creative_assets(run)
            or []
        )
        creative_direction = dict(
            post_package.get("creative_direction")
            or self._get_creative_direction(run)
            or {}
        )
        brand_foundation = dict(
            post_package.get("brand_foundation_snapshot")
            or self._get_brand_foundation(run)
            or {}
        )
        brand_map = dict(post_package.get("brand_map") or self._get_brand_map(run) or {})
        visual_assets = dict(post_package.get("visual_assets") or {})

        assets_by_type: Dict[str, list[Dict[str, Any]]] = {}
        for asset in creative_assets:
            if not isinstance(asset, dict):
                continue

            asset_type = str(
                asset.get("type")
                or asset.get("asset_type")
                or asset.get("intent")
                or "reference"
            ).strip().lower()

            if not asset_type:
                asset_type = "reference"

            assets_by_type.setdefault(asset_type, []).append(asset)

        visual_assets.update(
            {
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "assets_by_type": assets_by_type,
                "brand_foundation_snapshot": brand_foundation,
                "brand_map": brand_map,
            }
        )

        result = self.image_generation_service.generate_marketing_carousel_cards(
            caption=str(post_package.get("caption") or ""),
            carousel=list(post_package.get("carousel") or []),
            provider="openai",
            model=str(post_package.get("selected_image_model") or "gpt-image-1"),
            size="1024x1536",
            background="opaque",
            output_format="png",
            file_stem_prefix=f"{run.id}_{self._step_id(step)}",
            metadata={
                "workspace_id": run.workspace_id,
                "workflow_id": run.workflow_id,
                "workflow_run_id": run.id,
                "run_id": run.id,
                "step_id": self._step_id(step),
                "department_key": run.department_key,
                "primary_channel": str(post_package.get("primary_channel") or "facebook"),
                "channel": str(post_package.get("primary_channel") or "facebook"),
                "creative_assets_count": len(creative_assets),
                "creative_asset_types": sorted(assets_by_type.keys()),
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "brand_foundation_snapshot": brand_foundation,
                "brand_map": brand_map,
            },
            visual_assets=visual_assets,
            brand_name=str(
                post_package.get("brand_name")
                or post_package.get("page_name")
                or post_package.get("business_name")
                or "Local business"
            ),
            primary_channel=str(post_package.get("primary_channel") or "Facebook"),
            offer=post_package.get("offer"),
            audience=post_package.get("target_audience"),
            persona=post_package.get("persona"),
            objective=post_package.get("objective"),
        )

        if not result.get("ok") and not result.get("cards"):
            raise RuntimeError(str(result.get("error") or "carousel_image_generation_failed"))

        cards = list(result.get("cards") or [])
        generated_images = [
            {
                "card_index": card.get("card_index"),
                "card_type": card.get("card_type"),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "status": card.get("status", "completed"),
                "url": card.get("asset_url") or card.get("image_url") or card.get("file_path"),
                "asset_url": card.get("asset_url") or card.get("image_url"),
                "asset_id": card.get("asset_id"),
                "file_path": card.get("file_path"),
                "mime_type": card.get("mime_type"),
                "error": card.get("error"),
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "brand_foundation_snapshot": brand_foundation,
                "brand_map": brand_map,
            }
            for card in cards
        ]

        primary_generated_image = next(
            (
                image
                for image in generated_images
                if str(image.get("status") or "").lower() == "completed"
            ),
            generated_images[0] if generated_images else None,
        )

        return {
            "provider": result.get("provider"),
            "model": result.get("model"),
            "status": "completed" if result.get("ok") else "partial",
            "generated_image": primary_generated_image,
            "generated_images": generated_images,
            "carousel_cards": cards,
            "creative_assets": creative_assets,
            "creative_direction": creative_direction,
            "assets_by_type": assets_by_type,
            "visual_assets": visual_assets,
            "brand_foundation_snapshot": brand_foundation,
            "brand_map": brand_map,
            "error": result.get("error"),
        }

    def _simulate_step_output(
        self,
        *,
        run: WorkflowRun,
        workflow: WorkflowDefinition,
        step: WorkflowStepDefinition,
    ) -> Dict[str, Any]:
        kind = self._step_kind(step)
        config = self._step_config(step)
        step_id = self._step_id(step)

        if kind in {"start", "input"}:
            return {
                "ok": True,
                "message": "Input captured",
                "input_payload": dict(run.input_payload or {}),
                "context": dict(run.context or {}),
            }

        if kind in {"draft_content", "llm_task"}:
            brief = (
                run.input_payload.get("brief")
                or run.context.get("brief")
                or workflow.name
            )
            output_key = str(config.get("output_key") or "")

            marketing_strategy = dict(run.input_payload.get("marketing_strategy") or {})
            brand_foundation = self._get_brand_foundation(run)
            brand_map = self._get_brand_map(run)
            department_notes = dict(run.input_payload.get("department_notes") or {})

            platform_strategy = self._get_platform_strategy(
                marketing_strategy=marketing_strategy,
                brand_foundation=brand_foundation,
                brand_map=brand_map,
            )
            audience_objective = self._get_audience_objective(
                marketing_strategy=marketing_strategy,
                brand_foundation=brand_foundation,
                brand_map=brand_map,
            )
            creative_system = self._get_creative_system(brand_map)
            visual_identity = self._get_visual_identity(brand_map)
            rule_context = self._get_rule_context(
                marketing_strategy=marketing_strategy,
                brand_foundation=brand_foundation,
                brand_map=brand_map,
                department_notes=department_notes,
            )

            creative_assets = self._get_creative_assets(run)
            creative_direction = self._get_creative_direction(run)
            creative_asset_prompt_block = self._build_creative_asset_prompt_block(run)
            brand_prompt_block = self._build_brand_prompt_block(
                marketing_strategy=marketing_strategy,
                brand_foundation=brand_foundation,
                brand_map=brand_map,
                department_notes=department_notes,
            )

            channels = platform_strategy.get("channels") or []
            hashtags = platform_strategy.get("hashtags") or []
            keywords = platform_strategy.get("keywords") or []
            hard_rules = rule_context.get("hard_rules") or []
            guidance_notes = rule_context.get("guidance_notes") or []
            campaign_notes = rule_context.get("campaign_notes") or []
            voice_tone = rule_context.get("voice_tone") or []
            avoid = rule_context.get("avoid") or []

            product_name = creative_direction.get("product_name")
            offer_price = creative_direction.get("offer_price")
            offer_details = creative_direction.get("offer_details")
            usage_notes = creative_direction.get("usage_notes")
            style_direction = creative_direction.get("style_direction")
            asset_intent = creative_direction.get("asset_intent")

            font_rules = self._string_list(
                visual_identity.get("font_rules")
                or visual_identity.get("fontRules")
                or visual_identity.get("fonts")
                or visual_identity.get("typography")
                or []
            )
            colour_rules = self._string_list(
                visual_identity.get("colour_rules")
                or visual_identity.get("color_rules")
                or visual_identity.get("colourRules")
                or visual_identity.get("colorRules")
                or visual_identity.get("colours")
                or visual_identity.get("colors")
                or []
            )

            creative_context_lines = []
            if brand_prompt_block:
                creative_context_lines.append(brand_prompt_block)
            if creative_asset_prompt_block:
                creative_context_lines.append(creative_asset_prompt_block)
            if asset_intent:
                creative_context_lines.append(f"Asset intent: {asset_intent}")
            if product_name:
                creative_context_lines.append(f"Product / subject: {product_name}")
            if offer_price:
                creative_context_lines.append(f"Offer price: {offer_price}")
            if offer_details:
                creative_context_lines.append(f"Offer details: {offer_details}")
            if style_direction:
                creative_context_lines.append(f"Style direction: {style_direction}")
            if usage_notes:
                creative_context_lines.append(f"Image usage notes: {usage_notes}")
            if font_rules:
                creative_context_lines.append("Font rules: " + "; ".join(font_rules))
            if colour_rules:
                creative_context_lines.append("Colour rules: " + "; ".join(colour_rules))

            creative_context = "\n".join(
                str(line).strip() for line in creative_context_lines if str(line).strip()
            )

            creative_context_block = (
                f"Brand / creative context:\n{creative_context}\n"
                if creative_context
                else ""
            )

            objective = audience_objective.get("objective") or ""
            funnel_goal = audience_objective.get("funnel_goal") or ""
            target_audience = audience_objective.get("target_audience") or ""
            persona = audience_objective.get("persona") or ""
            offer = audience_objective.get("offer") or ""

            if output_key == "draft_caption":
                prompt = (
                    "Write the final social media caption only.\n\n"
                    f"Brief: {brief}\n"
                    f"Objective: {objective}\n"
                    f"Funnel goal: {funnel_goal}\n"
                    f"Audience: {target_audience}\n"
                    f"Persona: {persona}\n"
                    f"Offer: {offer}\n"
                    f"Channels: {', '.join(str(x) for x in channels) if channels else 'General'}\n"
                    f"Hashtags: {', '.join(str(x) for x in hashtags) if hashtags else 'None'}\n"
                    f"Keywords: {', '.join(str(x) for x in keywords) if keywords else 'None'}\n"
                    f"Voice / tone: {' | '.join(str(x) for x in voice_tone) if voice_tone else 'None'}\n"
                    f"Hard rules: {' | '.join(str(x) for x in hard_rules) if hard_rules else 'None'}\n"
                    f"Guidance notes: {' | '.join(str(x) for x in guidance_notes) if guidance_notes else 'None'}\n"
                    f"Campaign notes: {' | '.join(str(x) for x in campaign_notes) if campaign_notes else 'None'}\n"
                    f"Avoid: {' | '.join(str(x) for x in avoid) if avoid else 'None'}\n"
                    f"{creative_context_block}\n"
                    "Requirements:\n"
                    "- Produce real publish-ready copy, not a plan.\n"
                    "- Do not describe what you are doing.\n"
                    "- Do not say 'Draft request', 'Context', 'Plan', or similar.\n"
                    "- Use the platform strategy, audience objective, brand rules, and creative direction as hard context.\n"
                    "- Use the creative assets and direction as concrete constraints, not optional inspiration.\n"
                    "- Mention the product, offer, price, variants, or usage notes when provided and relevant.\n"
                    "- Keep it concise, persuasive, and audience-aware.\n"
                    "- End with a practical CTA.\n"
                    "- Return only the final caption text."
                )

            elif output_key == "draft_carousel":
                prompt = (
                    "Create the final publish-ready 5-card carousel copy.\n\n"
                    f"Brief: {brief}\n"
                    f"Objective: {objective}\n"
                    f"Funnel goal: {funnel_goal}\n"
                    f"Audience: {target_audience}\n"
                    f"Persona: {persona}\n"
                    f"Offer: {offer}\n"
                    f"Channels: {', '.join(str(x) for x in channels) if channels else 'General'}\n"
                    f"Keywords: {', '.join(str(x) for x in keywords) if keywords else 'None'}\n"
                    f"Voice / tone: {' | '.join(str(x) for x in voice_tone) if voice_tone else 'None'}\n"
                    f"Hard rules: {' | '.join(str(x) for x in hard_rules) if hard_rules else 'None'}\n"
                    f"Guidance notes: {' | '.join(str(x) for x in guidance_notes) if guidance_notes else 'None'}\n"
                    f"Campaign notes: {' | '.join(str(x) for x in campaign_notes) if campaign_notes else 'None'}\n"
                    f"Avoid: {' | '.join(str(x) for x in avoid) if avoid else 'None'}\n"
                    f"{creative_context_block}\n"
                    "Requirements:\n"
                    "- Produce real carousel card copy, not commentary about the task.\n"
                    "- Use exactly 5 cards.\n"
                    "- Each card must be short, direct, and ready to place on artwork.\n"
                    "- Structure as: Hook / Problem / Solution / Proof / CTA.\n"
                    "- Use the platform strategy, audience objective, brand rules, and creative direction as hard context.\n"
                    "- Respect font and colour rules when wording implies visual emphasis.\n"
                    "- Build the carousel around the provided product, offer, asset intent, and image usage notes when present.\n"
                    "- Do not include headings like 'Card 1:' or any extra explanation.\n"
                    "- Return one card per line only."
                )

            else:
                prompt = (
                    "Draft the final marketing content only.\n\n"
                    f"Brief: {brief}\n"
                    f"Objective: {objective}\n"
                    f"Audience: {target_audience}\n"
                    f"Offer: {offer}\n"
                    f"Channels: {', '.join(str(x) for x in channels) if channels else 'General'}\n"
                    f"{creative_context_block}\n"
                    "Return only the final publish-ready content."
                )

            agent_id = self._safe_agent_id(run, workflow)
            resolved_objective = self._safe_objective(
                workflow=workflow,
                brief=str(brief or ""),
                marketing_strategy=marketing_strategy,
                brand_foundation=brand_foundation,
            )
            model_preferences = self._resolve_model_preferences(
                run=run,
                workflow=workflow,
                marketing_strategy=marketing_strategy,
                brand_foundation=brand_foundation,
                step_config=config,
            )

            skill_input_payload: Dict[str, Any] = {
                "title": workflow.name,
                "prompt": prompt,
                "system_prompt": (
                    "You are a direct-response marketing copywriter. "
                    "Produce only final publish-ready copy. "
                    "Use supplied brand foundation, platform strategy, audience objective, "
                    "creative direction, font rules, colour rules, visual identity, product context, "
                    "image usage notes, offer details, and style direction as hard campaign context. "
                    "Never explain the plan, never echo the instructions, "
                    "and never output meta commentary."
                ),
                "capability": "drafting",
                "workspace_id": run.workspace_id,
                "metadata": {
                    "workspace_id": run.workspace_id,
                    "workspace_name": run.workspace_id,
                    "workflow_id": run.workflow_id,
                    "workflow_run_id": run.id,
                    "agent_id": agent_id,
                    "department_key": run.department_key,
                    "step_id": step_id,
                    "step_kind": kind,
                    "output_key": output_key,
                    "selected_provider": model_preferences.get("selected_provider"),
                    "selected_model": model_preferences.get("selected_model"),
                    "brief": brief,
                    "objective": objective,
                    "funnel_goal": funnel_goal,
                    "target_audience": target_audience,
                    "persona": persona,
                    "offer": offer,
                    "channels": channels,
                    "hashtags": hashtags,
                    "keywords": keywords,
                    "hard_rules": hard_rules,
                    "guidance_notes": guidance_notes,
                    "campaign_notes": campaign_notes,
                    "voice_tone": voice_tone,
                    "avoid": avoid,
                    "platform_strategy": platform_strategy,
                    "audience_objective": audience_objective,
                    "creative_system": creative_system,
                    "visual_identity": visual_identity,
                    "brand_foundation_snapshot": brand_foundation,
                    "brand_map": brand_map,
                    "creative_assets": creative_assets,
                    "creative_direction": creative_direction,
                    "asset_intent": asset_intent,
                    "product_name": product_name,
                    "offer_price": offer_price,
                    "offer_details": offer_details,
                    "usage_notes": usage_notes,
                    "style_direction": style_direction,
                    "font_rules": font_rules,
                    "colour_rules": colour_rules,
                },
            }

            if model_preferences.get("selected_provider"):
                skill_input_payload["provider"] = model_preferences["selected_provider"]

            if model_preferences.get("selected_model"):
                skill_input_payload["preferred_model"] = model_preferences["selected_model"]

            if model_preferences.get("model_policy_ref"):
                skill_input_payload["model_policy_ref"] = model_preferences["model_policy_ref"]

            skill_request = SkillRunRequest(
                skill_id="draft_content",
                agent_id=agent_id,
                task_id=run.id,
                objective=resolved_objective,
                input_payload=skill_input_payload,
                allowed_tools=[],
                allowed_containers=[],
                trace_required=True,
            )

            result = self.draft_content_skill.run(skill_request)
            result_output = dict(result.output_payload or {})
            drafted_text = str(result_output.get("draft") or "").strip()

            common_output = {
                "channels": channels,
                "hashtags": hashtags,
                "keywords": keywords,
                "platform_strategy": platform_strategy,
                "audience_objective": audience_objective,
                "creative_system": creative_system,
                "visual_identity": visual_identity,
                "brand_foundation_snapshot": brand_foundation,
                "brand_map": brand_map,
                "brandMap": brand_map,
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "provider": result_output.get("provider"),
                "model": result_output.get("model"),
                "usage": result_output.get("usage"),
                "fallback_used": result_output.get("fallback_used"),
                "policy_id": result_output.get("policy_id"),
                "selected_provider": model_preferences.get("selected_provider"),
                "selected_model": model_preferences.get("selected_model"),
            }

            if output_key == "draft_caption":
                run.context["draft_caption"] = drafted_text
                run.context["creative_assets"] = creative_assets
                run.context["creative_direction"] = creative_direction
                run.context["brand_foundation_snapshot"] = brand_foundation
                run.context["brand_map"] = brand_map

                return {
                    "ok": True,
                    "draft_caption": drafted_text,
                    **common_output,
                }

            if output_key == "draft_carousel":
                carousel = [
                    line.strip("-• \t")
                    for line in drafted_text.splitlines()
                    if line.strip()
                ]

                if len(carousel) < 5:
                    carousel = [
                        carousel[0] if len(carousel) > 0 else f"{brief}",
                        carousel[1] if len(carousel) > 1 else "Problem",
                        carousel[2] if len(carousel) > 2 else "Solution",
                        carousel[3] if len(carousel) > 3 else "Proof",
                        carousel[4] if len(carousel) > 4 else "CTA",
                    ]

                carousel = carousel[:5]
                run.context["draft_carousel"] = carousel
                run.context["creative_assets"] = creative_assets
                run.context["creative_direction"] = creative_direction
                run.context["brand_foundation_snapshot"] = brand_foundation
                run.context["brand_map"] = brand_map

                return {
                    "ok": True,
                    "draft_carousel": carousel,
                    **common_output,
                }

            generic_output = {
                "ok": True,
                "draft": drafted_text,
                **common_output,
            }

            if output_key:
                run.context[output_key] = generic_output

            run.context["creative_assets"] = creative_assets
            run.context["creative_direction"] = creative_direction
            run.context["brand_foundation_snapshot"] = brand_foundation
            run.context["brand_map"] = brand_map

            return generic_output

        if kind in {"approval", "approval_checkpoint"}:
            return {
                "ok": True,
                "message": "Approval checkpoint passed",
                "approval_packet": run.context.get("approval_packet"),
                "creative_assets": self._get_creative_assets(run),
                "creative_direction": self._get_creative_direction(run),
                "brand_foundation_snapshot": self._get_brand_foundation(run),
                "brand_map": self._get_brand_map(run),
            }

        if kind == "send_email":
            return {"ok": True, "message": "Email send simulated"}

        if kind == "post_social":
            post_package = (
                run.result_payload.get("post_package")
                if isinstance(run.result_payload, dict)
                else None
            ) or run.context.get("post_package")

            if not isinstance(post_package, dict):
                post_package = self._build_marketing_post_package(run)

            brand_foundation = self._get_brand_foundation(run)
            brand_map = self._get_brand_map(run)
            creative_assets = self._get_creative_assets(run)
            creative_direction = self._get_creative_direction(run)
            creative_asset_prompt_block = self._build_creative_asset_prompt_block(run)
            brand_prompt_block = self._build_brand_prompt_block(
                marketing_strategy=dict(run.input_payload.get("marketing_strategy") or {}),
                brand_foundation=brand_foundation,
                brand_map=brand_map,
                department_notes=dict(run.input_payload.get("department_notes") or {}),
            )

            post_package["brand_foundation_snapshot"] = brand_foundation
            post_package["brand_map"] = brand_map
            post_package["brandMap"] = brand_map
            post_package["creative_assets"] = creative_assets
            post_package["creative_direction"] = creative_direction

            visual_assets = dict(post_package.get("visual_assets") or {})
            visual_assets["brand_foundation_snapshot"] = brand_foundation
            visual_assets["brand_map"] = brand_map
            visual_assets["creative_assets"] = creative_assets
            visual_assets["creative_direction"] = creative_direction
            post_package["visual_assets"] = visual_assets

            image_prompt = (
                post_package.get("image_prompt")
                or f"Create a clean social media visual for: {post_package.get('brief') or workflow.name}"
            )

            for block in (brand_prompt_block, creative_asset_prompt_block):
                if block and block not in str(image_prompt):
                    image_prompt = f"{image_prompt}\n\n{block}"

            post_package["image_prompt"] = str(image_prompt)

            generated_image: Optional[Dict[str, Any]] = None
            generated_images: list[Dict[str, Any]] = []
            carousel_cards: list[Dict[str, Any]] = []
            image_generation = dict(post_package.get("image_generation") or {})

            should_generate_image = bool(config.get("generate_image", True))
            requested_image_provider = str(
                config.get("image_provider")
                or image_generation.get("provider")
                or post_package.get("selected_image_provider")
                or "openai"
            )
            requested_image_model = str(
                config.get("image_model")
                or image_generation.get("model")
                or post_package.get("selected_image_model")
                or "gpt-image-1"
            )

            is_carousel = (
                str(post_package.get("visual_type") or "").lower() == "carousel"
                or len(list(post_package.get("carousel") or [])) > 1
            )

            if should_generate_image:
                try:
                    if requested_image_provider == "openai":
                        if is_carousel:
                            carousel_result = self._generate_openai_marketing_carousel_cards(
                                run=run,
                                workflow=workflow,
                                step=step,
                                post_package=post_package,
                            )
                            generated_image = carousel_result.get("generated_image")
                            generated_images = list(carousel_result.get("generated_images") or [])
                            carousel_cards = list(carousel_result.get("carousel_cards") or [])

                            image_generation.update(
                                {
                                    "provider": requested_image_provider,
                                    "model": requested_image_model,
                                    "status": carousel_result.get("status", "completed"),
                                    "asset_url": (
                                        generated_image.get("asset_url")
                                        if isinstance(generated_image, dict)
                                        else None
                                    ),
                                    "asset_id": (
                                        generated_image.get("asset_id")
                                        if isinstance(generated_image, dict)
                                        else None
                                    ),
                                    "error": carousel_result.get("error"),
                                    "cards_generated": len(carousel_cards),
                                }
                            )
                        else:
                            generated_image = self._generate_openai_marketing_image(
                                prompt=str(image_prompt),
                                run=run,
                                workflow=workflow,
                                step=step,
                            )
                            image_generation.update(
                                {
                                    "provider": generated_image.get(
                                        "provider",
                                        requested_image_provider,
                                    ),
                                    "model": generated_image.get(
                                        "model",
                                        requested_image_model,
                                    ),
                                    "status": generated_image.get(
                                        "status",
                                        "completed",
                                    ),
                                    "asset_url": generated_image.get("url"),
                                    "asset_id": generated_image.get("file_path"),
                                    "error": None,
                                }
                            )
                    else:
                        raise RuntimeError(
                            f"unsupported_image_provider: {requested_image_provider}"
                        )

                    if generated_image:
                        post_package["generated_image"] = generated_image
                    if generated_images:
                        post_package["generated_images"] = generated_images
                    if carousel_cards:
                        post_package["carousel_cards"] = carousel_cards

                except Exception as exc:
                    image_generation.update(
                        {
                            "provider": requested_image_provider,
                            "model": requested_image_model,
                            "status": "failed",
                            "asset_url": None,
                            "asset_id": None,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
            else:
                image_generation.update(
                    {
                        "provider": requested_image_provider,
                        "model": requested_image_model,
                        "status": "skipped",
                        "asset_url": None,
                        "asset_id": None,
                        "error": None,
                    }
                )

            post_package["image_generation"] = image_generation
            run.context["post_package"] = post_package
            run.result_payload["post_package"] = post_package

            run.context["publish_result"] = {
                "status": "simulated",
                "published": False,
                "channels": (
                    post_package.get("channels")
                    if isinstance(post_package, dict)
                    else []
                ),
                "generated_image": generated_image,
                "generated_images": generated_images,
                "carousel_cards": carousel_cards,
                "image_generation": image_generation,
                "creative_assets": creative_assets,
                "creative_direction": creative_direction,
                "brand_foundation_snapshot": brand_foundation,
                "brand_map": brand_map,
                "brandMap": brand_map,
            }

            return {
                "ok": True,
                "message": "Social post simulated",
                "post_package": post_package,
                "publish_result": run.context["publish_result"],
            }

        if kind == "update_crm":
            return {"ok": True, "message": "CRM update simulated"}

        if kind == "create_document":
            return {"ok": True, "message": "Document creation simulated"}

        if kind == "wait":
            return {"ok": True, "message": "Wait step completed"}

        if kind == "complete":
            return {
                "ok": True,
                "message": "Workflow completed",
                "post_package": run.context.get("post_package"),
                "approval_decision": run.context.get("approval_decision"),
                "creative_assets": self._get_creative_assets(run),
                "creative_direction": self._get_creative_direction(run),
                "brand_foundation_snapshot": self._get_brand_foundation(run),
                "brand_map": self._get_brand_map(run),
            }

        return {"ok": True, "message": f"Step executed: {kind}"}

    def resolve_approval(
        self,
        *,
        workspace_id: str,
        approval_id: str,
        approve: bool,
        resolved_by: str,
        resolution_note: Optional[str] = None,
    ) -> Optional[ApprovalRequest]:
        return self.approval_request_repository.resolve(
            workspace_id,
            approval_id,
            approve=approve,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
            resolved_at=_utc_now_iso(),
        )

    def resume_run_after_approval(
        self,
        workflow: WorkflowDefinition,
        run_id: str,
    ) -> WorkflowRun:
        run = self.workflow_run_repository.load(workflow.workspace_id, run_id)

        if not run.approval_request_id:
            return run

        approval = self.approval_request_repository.find_one(
            run.workspace_id,
            run.approval_request_id,
        )
        if approval is None:
            return run

        approval_decision = {
            "approval_id": approval.id,
            "status": approval.status,
            "resolved_by": approval.resolved_by,
            "resolution_note": approval.resolution_note,
            "resolved_at": approval.resolved_at,
        }
        run.context["approval_decision"] = approval_decision
        run.result_payload["approval_decision"] = approval_decision

        if approval.status == "rejected":
            run.status = "cancelled"
            run.updated_at = _utc_now_iso()
            run.error_message = "Run rejected at approval checkpoint"
            run.result_payload["post_package"] = self._build_marketing_post_package(run)
            return self.workflow_run_repository.save(run)

        if approval.status != "approved":
            return self.workflow_run_repository.save(run)

        run.status = "running"
        run.approval_request_id = None
        run.updated_at = _utc_now_iso()
        run.result_payload["post_package"] = self._build_marketing_post_package(run)
        run = self.workflow_run_repository.save(run)
        return self._advance_from_current_step(workflow, run.id)

    def _advance_from_current_step(
        self,
        workflow: WorkflowDefinition,
        run_id: str,
    ) -> WorkflowRun:
        run = self.workflow_run_repository.load(workflow.workspace_id, run_id)
        current = workflow.get_step(run.current_step_id or "")
        if current is None:
            run.result_payload["post_package"] = self._build_marketing_post_package(run)
            return self.workflow_run_repository.save(run)

        next_step_id = self._step_next_id(current)
        run.current_step_id = next_step_id
        run.updated_at = _utc_now_iso()
        run.result_payload["post_package"] = self._build_marketing_post_package(run)
        run = self.workflow_run_repository.save(run)

        if not next_step_id:
            run.status = "completed"
            run.completed_at = _utc_now_iso()
            run.updated_at = run.completed_at
            run.result_payload["post_package"] = self._build_marketing_post_package(run)
            return self.workflow_run_repository.save(run)

        return self.execute_next(workflow, run.id)

    def cancel_run(
        self,
        *,
        workspace_id: str,
        run_id: str,
        reason: str = "cancelled",
    ) -> WorkflowRun:
        run = self.workflow_run_repository.load(workspace_id, run_id)
        run.status = "cancelled"
        run.error_message = reason
        run.updated_at = _utc_now_iso()
        return self.workflow_run_repository.save(run)