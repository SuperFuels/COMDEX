from __future__ import annotations

from typing import Any, Dict

from backend.modules.aion_agents.contracts.agent_definition import AgentDefinition
from backend.modules.aion_agents.contracts.trigger_definition import TriggerDefinition
from backend.modules.aion_agents.contracts.workflow_definition import (
    WorkflowDefinition,
    WorkflowStepDefinition,
)
from backend.modules.local_node.contracts_local_node import utc_now_iso


def build_marketing_content_workflow(
    workspace_id: str,
    *,
    workflow_id: str = "workflow_marketing_content_draft_v1",
) -> WorkflowDefinition:
    return WorkflowDefinition(
        id=workflow_id,
        workspace_id=workspace_id,
        name="Marketing Content Draft v1",
        version=2,
        department_key="marketing",
        description=(
            "Generate publish-ready marketing draft content, route through approval, "
            "then simulate publish packaging with generated image metadata."
        ),
        execution_mode="draft_and_approval",
        active=True,
        tags=[
            "marketing",
            "content",
            "draft",
            "approval",
            "post",
            "image",
        ],
        steps=[
            WorkflowStepDefinition(
                id="capture_brief",
                kind="start",
                name="Capture brief",
                next_step_id="draft_caption",
                config={
                    "required_fields": [
                        "brief",
                        "marketing_strategy",
                        "brand_foundation_snapshot",
                    ],
                    "notes": (
                        "Input payload should carry the marketing brief, strategy, "
                        "brand foundation snapshot, optional department notes, and "
                        "optional selected provider/model preferences."
                    ),
                },
            ),
            WorkflowStepDefinition(
                id="draft_caption",
                kind="draft_content",
                name="Draft caption",
                next_step_id="draft_carousel",
                config={
                    "task_kind": "draft",
                    "output_key": "draft_caption",
                    "content_format": "social_caption",
                    "requires_publish_ready_copy": True,
                },
            ),
            WorkflowStepDefinition(
                id="draft_carousel",
                kind="draft_content",
                name="Draft carousel",
                next_step_id="approval_gate",
                config={
                    "task_kind": "draft",
                    "output_key": "draft_carousel",
                    "content_format": "carousel_5_cards",
                    "requires_publish_ready_copy": True,
                },
            ),
            WorkflowStepDefinition(
                id="approval_gate",
                kind="approval_checkpoint",
                name="Approval gate",
                next_step_id="post_social",
                requires_approval=True,
                config={
                    "approval_kind": "marketing_publish_review",
                    "approval_class": "draft_review",
                    "pause_until_resolved": True,
                },
            ),
            WorkflowStepDefinition(
                id="post_social",
                kind="post_social",
                name="Prepare social post package",
                next_step_id="complete_run",
                config={
                    "publish_mode": "simulated",
                    "generate_image": True,
                    "image_provider": "openai",
                    "image_model": "gpt-image-1",
                    "attach_generated_image_to_post_package": True,
                },
            ),
            WorkflowStepDefinition(
                id="complete_run",
                kind="complete",
                name="Complete run",
                config={
                    "finalize_post_package": True,
                },
            ),
        ],
    )


def build_marketing_operator_agent(
    workspace_id: str,
    *,
    agent_id: str = "agent_marketing_operator_v1",
    workflow_id: str = "workflow_marketing_content_draft_v1",
) -> AgentDefinition:
    now = utc_now_iso()

    return AgentDefinition(
        id=agent_id,
        workspace_id=workspace_id,
        name="Marketing Operator v1",
        department_key="marketing",
        description=(
            "Bounded marketing operator for publish-ready caption/carousel drafting, "
            "approval-led execution, and simulated post packaging with image generation metadata."
        ),
        agent_type="operator",
        active=True,
        workflow_ids=[workflow_id],
        trigger_ids=["trigger_marketing_manual_launch_v1"],
        capability_keys=[
            "draft_marketing_caption",
            "draft_marketing_carousel",
            "generate_marketing_post_package",
            "generate_marketing_image",
            "submit_for_approval",
        ],
        policy={
            "allow_autonomous_publish": False,
            "allow_draft_generation": True,
            "allow_image_generation": True,
            "require_approval_for_public_actions": True,
            "default_publish_mode": "simulated",
            "default_local_model": "gemma",
            "default_image_provider": "openai",
            "default_image_model": "gpt-image-1",
        },
        metadata={
            "surface": "boardroom",
            "seat_hint": "marketing",
            "default_provider_strategy": "user_selected_or_local_default",
            "default_local_text_model": "gemma",
            "default_image_provider": "openai",
            "default_image_model": "gpt-image-1",
        },
        created_at=now,
        updated_at=now,
    )


def build_marketing_manual_trigger(
    workspace_id: str,
    *,
    trigger_id: str = "trigger_marketing_manual_launch_v1",
    workflow_id: str = "workflow_marketing_content_draft_v1",
    agent_id: str = "agent_marketing_operator_v1",
) -> TriggerDefinition:
    return TriggerDefinition(
        id=trigger_id,
        workspace_id=workspace_id,
        name="Marketing Manual Launch",
        trigger_type="manual",
        workflow_definition_id=workflow_id,
        agent_id=agent_id,
        active=True,
        config={
            "launch_surface": "boardroom",
            "department_key": "marketing",
            "launch_mode": "manual",
            "require_approval": True,
            "default_publish_mode": "simulated",
        },
    )


def build_marketing_seed_bundle(workspace_id: str) -> Dict[str, object]:
    workflow = build_marketing_content_workflow(workspace_id)
    agent = build_marketing_operator_agent(
        workspace_id,
        workflow_id=workflow.id,
    )
    trigger = build_marketing_manual_trigger(
        workspace_id,
        workflow_id=workflow.id,
        agent_id=agent.id,
    )

    return {
        "workflow": workflow,
        "agent": agent,
        "trigger": trigger,
    }


def seed_marketing_operator_bundle(
    *,
    workspace_id: str,
    workflow_definition_repository: Any,
    agent_definition_repository: Any,
    trigger_definition_repository: Any,
) -> Dict[str, object]:
    bundle = build_marketing_seed_bundle(workspace_id)

    workflow = bundle["workflow"]
    agent = bundle["agent"]
    trigger = bundle["trigger"]

    workflow_id = getattr(workflow, "id", None) or getattr(workflow, "workflow_id", None)
    agent_id = getattr(agent, "id", None) or getattr(agent, "agent_id", None)
    trigger_id = getattr(trigger, "trigger_id", None) or getattr(trigger, "id", None)

    existing_workflow = None
    if hasattr(workflow_definition_repository, "get"):
        existing_workflow = workflow_definition_repository.get(
            workspace_id,
            workflow_id,
        )
    elif hasattr(workflow_definition_repository, "find_one"):
        existing_workflow = workflow_definition_repository.find_one(
            workspace_id,
            workflow_id,
        )
    elif hasattr(workflow_definition_repository, "exists"):
        if workflow_definition_repository.exists(workspace_id, workflow_id):
            existing_workflow = workflow

    existing_agent = None
    if hasattr(agent_definition_repository, "find_one"):
        existing_agent = agent_definition_repository.find_one(
            workspace_id,
            agent_id,
        )
    elif hasattr(agent_definition_repository, "get"):
        existing_agent = agent_definition_repository.get(
            workspace_id,
            agent_id,
        )
    elif hasattr(agent_definition_repository, "exists"):
        if agent_definition_repository.exists(workspace_id, agent_id):
            existing_agent = agent

    existing_trigger = None
    if hasattr(trigger_definition_repository, "find_one"):
        existing_trigger = trigger_definition_repository.find_one(
            workspace_id,
            trigger_id,
        )
    elif hasattr(trigger_definition_repository, "get"):
        existing_trigger = trigger_definition_repository.get(
            workspace_id,
            trigger_id,
        )
    elif hasattr(trigger_definition_repository, "exists"):
        if trigger_definition_repository.exists(workspace_id, trigger_id):
            existing_trigger = trigger

    if existing_workflow is None:
        workflow_definition_repository.save(workflow)
    else:
        workflow_definition_repository.save(workflow)

    if existing_agent is None:
        agent_definition_repository.save(agent)
    else:
        agent_definition_repository.save(agent)

    if existing_trigger is None:
        trigger_definition_repository.save(trigger)
    else:
        trigger_definition_repository.save(trigger)

    return bundle