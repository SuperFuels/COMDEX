from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")


def _source() -> str:
    assert APP_JS.exists()
    return APP_JS.read_text(encoding="utf-8")


def test_intelligence_stack_is_part_of_existing_module_picker() -> None:
    text = _source()
    assert 'group: "Intelligence Stack"' in text
    assert 'group_id: "intelligence_stack"' in text
    for family in (
        "AION Brain",
        "Models",
        "Harnesses",
        "Compute",
        "Evidence",
        "Deliberation",
        "Governance",
        "Action & Verification",
    ):
        assert family in text


def test_intelligence_node_families_have_distinct_insertable_modules() -> None:
    text = _source()
    for module_id in (
        "intelligence.aion_admission",
        "intelligence.business_map",
        "intelligence.model_local",
        "intelligence.model_private_endpoint",
        "intelligence.harness",
        "intelligence.compute_target",
        "intelligence.evidence_retrieval",
        "intelligence.deterministic_validator",
        "intelligence.critic",
        "intelligence.reconcile",
        "intelligence.disclosure_gate",
        "intelligence.human_approval",
        "intelligence.capability",
        "intelligence.verify_receipt",
    ):
        assert f'id: "{module_id}"' in text


def test_picker_exposes_search_subgroups_preflight_badges_and_boundary_legend() -> None:
    text = _source()
    for contract in (
        'data-aion-architect-module-search="true"',
        "data-aion-intelligence-subgroup",
        "aion-boundary-legend",
        "aion-intelligence-module-badges",
        "module.credentials",
        "module.location",
        "module.cost",
        "module.risk",
        "module.requires_approval",
        "module.causes_external_effect",
    ):
        assert contract in text


def test_intelligence_nodes_preserve_metadata_in_existing_workflow_graph() -> None:
    text = _source()
    assert "getAionUnifiedRealNodeFromModule" in text
    assert 'intelligence_stack: module.group_id === "intelligence_stack"' in text
    for field in (
        "config_schema",
        "data_classes",
        "estimated_cost",
        "maturity",
        "modality",
        "domain",
        "licence",
        "causes_external_effect",
    ):
        assert field in text


def test_existing_full_node_editor_gets_schema_driven_intelligence_fields() -> None:
    text = _source()
    assert "installAionIntelligenceNodeEditorV1" in text
    assert "data-aion-intelligence-node-editor" in text
    assert "module.config_schema" in text
    assert "data-aion-intelligence-setting" in text
    assert "data-aion-intelligence-test-config" in text
    assert "data-aion-intelligence-reset-config" in text
    assert "Configuration schema valid. No workflow was executed." in text


def test_raw_credentials_are_rejected_and_only_vault_references_are_accepted() -> None:
    text = _source()
    assert "Raw credentials cannot be stored here" in text
    assert 'String(value).startsWith("vault://")' in text
    assert "mother-brain vault" in text
    assert "Raw secrets are prohibited from canvas state, autosave, logs, receipts and exports." in text


def test_consequential_node_execution_is_disabled_until_approved() -> None:
    text = _source()
    assert 'module.causes_external_effect && node.config?.approval_state !== "approved"' in text
    assert "Policy and exact approval are required before consequential execution." in text

