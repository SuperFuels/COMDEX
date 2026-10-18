from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
CONFIG = (ROOT / "desktop/mac/src/workflow/nodeEditor/configs/intelligenceConfig.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "desktop/mac/src/workflow/nodeEditor/configs/routerConfig.js").read_text(encoding="utf-8")


def test_canonical_node_editor_loads_intelligence_renderer_before_generic_configs():
    intelligence = INDEX.index("configs/intelligenceConfig.js")
    router = INDEX.index("configs/routerConfig.js")
    registry = INDEX.index("configs/index.js")
    assert intelligence < router < registry
    assert 'config.intelligence_stack === true' in CONFIG
    assert 'moduleId.startsWith("intelligence.")' in CONFIG


def test_intelligence_editor_renders_each_nodes_own_schema_and_governance_metadata():
    assert "config.config_schema" in CONFIG
    for marker in (
        "model_manifest_id",
        "context_limit",
        "endpoint_binding_ref",
        "harness_manifest_id",
        "source_bindings",
        "participant_bindings",
        "approval_surface",
        "verification_method",
        "data-aion-intelligence-config-native",
    ):
        assert marker in CONFIG


def test_private_model_router_cannot_be_misclassified_as_flow_router():
    assert 'actionId === "logic.router"' in ROUTER
    assert 'moduleId === "flow.router"' in ROUTER
    assert 'haystack.includes("router")' not in ROUTER


def test_intelligence_editor_rejects_raw_secrets_and_requires_vault_references():
    assert "Raw credentials cannot be stored here" in CONFIG
    assert 'startsWith("vault://")' in CONFIG
    assert "data-aion-vault-reference" in CONFIG


def test_intelligence_editor_can_select_or_create_an_encrypted_vault_binding():
    for marker in (
        "/api/vault/aion-flow/bindings",
        "data-aion-vault-binding-picker",
        "data-aion-vault-binding-new",
        "data-aion-vault-binding-secret",
        "create-aion-flow-binding-v1",
        "Only the resulting opaque reference is attached to this node",
    ):
        assert marker in CONFIG
    assert 'type="password"' in CONFIG
    assert 'body.binding.reference' in CONFIG
