from __future__ import annotations

from backend.modules.workflow_capsules.architect import (
    MissingConnectorWarning,
    WorkflowBuildPackAssembler,
    WorkflowBuilderGraphCompiler,
    WorkflowBuilderSpec,
    WorkflowBuilderSpecValidator,
    WorkflowEdgeSpec,
    WorkflowStepSpec,
)


def _valid_spec() -> WorkflowBuilderSpec:
    return WorkflowBuilderSpec(
        workflow_name="Gmail Customer Reply Workflow",
        goal="Handle new customer enquiries from Gmail and prepare safe follow-up actions.",
        connectors_required=["gmail", "hubspot", "calendly"],
        missing_connectors=[
            MissingConnectorWarning(
                connector="calendly",
                reason="Scheduling requested but Calendly is not connected.",
                step_id="schedule_call_placeholder",
            )
        ],
        steps=[
            WorkflowStepSpec(
                step_id="trigger_new_gmail",
                node_type="gmail.read",
                label="Watch Gmail inbox",
                connector="gmail",
                config={
                    "account": "newcustomer@example.com",
                    "trigger": "new_email",
                },
                risk_tier="low",
                requires_approval=False,
            ),
            WorkflowStepSpec(
                step_id="extract_customer_details",
                node_type="extract_fields",
                label="Extract customer details",
                config={
                    "fields": ["name", "email", "phone", "business_name", "enquiry_type"],
                },
                risk_tier="low",
                requires_approval=False,
            ),
            WorkflowStepSpec(
                step_id="upsert_hubspot_lead",
                node_type="hubspot.upsert_contact",
                label="Create or update HubSpot lead",
                connector="hubspot",
                config={
                    "email": "{{extract_customer_details.email}}",
                    "name": "{{extract_customer_details.name}}",
                    "phone": "{{extract_customer_details.phone}}",
                },
                risk_tier="medium",
                requires_approval=False,
            ),
            WorkflowStepSpec(
                step_id="compose_welcome_email",
                node_type="compose_string",
                label="Draft welcome email text",
                config={
                    "template_ref": "welcome_email_template",
                },
                risk_tier="low",
                requires_approval=False,
            ),
            WorkflowStepSpec(
                step_id="approval_before_draft",
                node_type="human_approval",
                label="Approve before creating Gmail draft",
                config={
                    "reason": "External customer email draft requires approval.",
                },
                risk_tier="medium",
                requires_approval=True,
            ),
            WorkflowStepSpec(
                step_id="create_gmail_draft",
                node_type="gmail.create_draft",
                label="Create Gmail draft",
                connector="gmail",
                config={
                    "to": "{{extract_customer_details.email}}",
                    "body": "{{compose_welcome_email.output}}",
                },
                risk_tier="medium",
                requires_approval=True,
            ),
            WorkflowStepSpec(
                step_id="schedule_call_placeholder",
                node_type="missing_connector_placeholder",
                label="Calendly scheduling placeholder",
                config={
                    "connector": "calendly",
                    "reason": "Calendly is not connected yet.",
                },
                risk_tier="blocked",
                requires_approval=True,
                connector="calendly",
                missing_connector=True,
            ),
        ],
        edges=[
            WorkflowEdgeSpec("trigger_new_gmail", "extract_customer_details"),
            WorkflowEdgeSpec("extract_customer_details", "upsert_hubspot_lead"),
            WorkflowEdgeSpec("upsert_hubspot_lead", "compose_welcome_email"),
            WorkflowEdgeSpec("compose_welcome_email", "approval_before_draft"),
            WorkflowEdgeSpec("approval_before_draft", "create_gmail_draft"),
            WorkflowEdgeSpec("extract_customer_details", "schedule_call_placeholder"),
        ],
    )


def test_workflow_build_pack_contains_context_rules_registry_and_schema() -> None:
    pack = WorkflowBuildPackAssembler().assemble(
        workflow_goal="Create a Gmail customer reply workflow.",
        user_steps=[
            {"action": "watch Gmail inbox", "source": "newcustomer@example.com"},
            {"action": "create or update HubSpot lead"},
        ],
        business_context={
            "business_name": "Demo Business",
            "industry": "local services",
            "services": ["repairs", "maintenance"],
            "tone_of_voice": "friendly and professional",
        },
        connected_credentials=["gmail", "hubspot"],
        missing_credentials=["calendly"],
    ).to_dict()

    assert pack["business_context"]["business_name"] == "Demo Business"
    assert pack["user_task"]["workflow_goal"] == "Create a Gmail customer reply workflow."
    assert "gmail" in pack["credentials"]["connected"]
    assert "calendly" in pack["credentials"]["missing"]

    assert "gmail.read" in pack["node_registry"]
    assert "gmail.create_draft" in pack["node_registry"]
    assert "hubspot.upsert_contact" in pack["node_registry"]

    assert pack["permission_runtime_rules"]["dry_run_first"] is True
    assert pack["permission_runtime_rules"]["live_send_disabled"] is True
    assert pack["required_output_schema"]["strict_json_only"] is True
    assert pack["required_output_schema"]["no_invented_node_types"] is True


def test_valid_workflow_builder_spec_passes_validation() -> None:
    result = WorkflowBuilderSpecValidator().validate(
        _valid_spec(),
        connected_credentials=["gmail", "hubspot"],
    )

    assert result.ok is True
    assert result.errors == []
    assert "schedule_call_placeholder" not in str(result.errors)
    assert result.audit["step_count"] == 7
    assert "create_gmail_draft" in result.audit["external_write_steps"]
    assert "approval_before_draft" in result.audit["approval_steps"]


def test_unknown_node_type_fails_closed() -> None:
    spec = _valid_spec()
    spec.steps[0].node_type = "made_up.super_power"

    result = WorkflowBuilderSpecValidator().validate(
        spec,
        connected_credentials=["gmail", "hubspot"],
    )

    assert result.ok is False
    assert "unknown_node_type:made_up.super_power" in result.errors


def test_live_send_or_arbitrary_code_fails_closed() -> None:
    spec = _valid_spec()
    spec.steps[-1].config["unsafe"] = "users.messages.send"
    spec.steps[-1].notes = "please exec('send live email')"

    result = WorkflowBuilderSpecValidator().validate(
        spec,
        connected_credentials=["gmail", "hubspot"],
    )

    assert result.ok is False
    assert any(error.startswith("forbidden_token:") for error in result.errors)


def test_external_write_without_approval_checkpoint_fails_closed() -> None:
    spec = _valid_spec()
    spec.steps = [step for step in spec.steps if step.node_type != "human_approval"]
    for step in spec.steps:
        step.requires_approval = False

    result = WorkflowBuilderSpecValidator().validate(
        spec,
        connected_credentials=["gmail", "hubspot"],
    )

    assert result.ok is False
    assert "external_write_without_approval_checkpoint" in result.errors


def test_missing_connector_compiles_to_placeholder_node() -> None:
    spec = _valid_spec()

    result = WorkflowBuilderGraphCompiler().compile(
        spec,
        connected_credentials=["gmail", "hubspot"],
    )

    assert result.ok is True
    assert result.capsule is not None

    nodes = {node["id"]: node for node in result.canvas["nodes"]}
    placeholder = nodes["schedule_call_placeholder"]

    assert placeholder["type"] == "missing_connector_placeholder"
    assert placeholder["data"]["missing_connector"] is True
    assert placeholder["data"]["connector"] == "calendly"
    assert "vault.calendly.credentials" in result.canvas["vault_requirements"]


def test_generated_graph_compiles_to_workflow_capsule_dry_run_safe() -> None:
    spec = _valid_spec()

    result = WorkflowBuilderGraphCompiler().compile(
        spec,
        connected_credentials=["gmail", "hubspot"],
    )

    assert result.ok is True

    capsule = result.capsule
    assert capsule.canonical_key.startswith("workflow:architect.")
    assert capsule.display_name == "Gmail Customer Reply Workflow"
    assert capsule.policy.dry_run_first is True
    assert "vault.gmail.credentials" in capsule.vault_requirements
    assert "vault.hubspot.credentials" in capsule.vault_requirements
    assert "vault.calendly.credentials" in capsule.vault_requirements

    step_kinds = [step["kind"] for step in capsule.compiled_glyph["steps"]]
    assert "read_email" in step_kinds
    assert "extract" in step_kinds
    assert "draft_content" in step_kinds
    assert "approval_checkpoint" in step_kinds
    assert "create_draft" in step_kinds

    combined = str(capsule.to_dict()).lower() if hasattr(capsule, "to_dict") else str(capsule).lower()
    assert "users.messages.send" not in combined
    assert "send_message" not in combined
    assert "live_send" not in combined
