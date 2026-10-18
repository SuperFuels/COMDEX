from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    make_workflow_capsule,
)
from backend.modules.workflow_capsules.habits.habit_capsule_registry import (
    HabitCapsuleRegistry,
)
from backend.modules.workflow_capsules.habits.habit_capsule_repository import (
    HabitCapsuleRepository,
)
from backend.modules.workflow_capsules.habits.habit_promotion_engine import (
    HabitPromotionEngine,
)
from backend.modules.workflow_capsules.global_registry.global_registry_store import (
    GlobalWorkflowRegistryStore,
)
from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    make_electrician_gmail_pack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    make_electrician_gmail_local_binding,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)
from backend.modules.workflow_capsules.resonance.workflow_capsule_feedback import (
    WorkflowCapsuleFeedbackEngine,
)


def _capsule(key: str, name: str, customer: str):
    return make_workflow_capsule(
        key,
        name,
        f"Follow up {customer} using the founder's private instructions.",
        tags=["customer", "follow-up"],
        workflow_graph={"customer": customer, "email": "private@example.test"},
    )


def test_workspace_capsules_and_learned_habits_use_guardian(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"c" * 32),
        actor_id="workflow-capsule-customer-content-test",
    )
    product_root = tmp_path / "application" / "workflow-capsules"
    repository = WorkflowCapsuleRepository(
        root=product_root,
        domain_store=store,
        workspace_id="acme",
    )

    core = _capsule(
        "workflow:tessaris.standard.follow_up.v1",
        "Tessaris standard follow-up",
        "a template customer",
    )
    private = _capsule(
        "workflow:acme.private.client.follow_up.v1",
        "Acme private client follow-up",
        "Private Client",
    )
    retained = _capsule(
        "workflow:retained.plaintext.customer.v1",
        "Retained plaintext customer capsule",
        "Old Private Client",
    )
    retained.save(
        repository.capsule_path(
            retained.canonical_key,
            scope="workspace",
            workspace_id="acme",
        )
    )

    core_saved = repository.save(core, scope="core")
    private_saved = repository.save(private, scope="workspace", workspace_id="acme")
    assert core_saved["path"].endswith(".workflow.wiki.phn")
    assert private_saved["path"].startswith(
        "vault://train_agent.automations/workflow_capsule_workspace_capsules/"
    )
    assert repository.load(retained.canonical_key, workspace_id="acme") is None
    assert repository.require(private.canonical_key, workspace_id="acme").display_name == (
        "Acme private client follow-up"
    )
    assert repository.save_index(workspace_id="acme")["derived_index_persisted"] is False
    glyph_registry = WorkflowGlyphRegistry(repository=repository)
    registry_result = glyph_registry.rebuild_and_save()
    assert registry_result["saved"]["derived_registry_persisted"] is False
    assert glyph_registry.require(private.canonical_key).display_name == (
        "Acme private client follow-up"
    )

    global_store = GlobalWorkflowRegistryStore(
        global_root=tmp_path / "application" / "global-workflow-packs",
        domain_store=store,
        workspace_id="acme",
    )
    pack_saved = global_store.save_industry_pack(make_electrician_gmail_pack())
    binding_saved = global_store.save_local_binding(
        make_electrician_gmail_local_binding(
            workspace_id="acme",
            business_id="Private Acme Electrical",
        )
    )
    assert pack_saved["path"].startswith(str(tmp_path / "application"))
    assert binding_saved["path"].startswith(
        "vault://train_agent.automations/workflow_capsule_local_bindings/"
    )
    assert GlobalWorkflowRegistryStore(
        global_root=tmp_path / "application" / "global-workflow-packs",
        domain_store=store,
        workspace_id="acme",
    ).require_local_binding(binding_saved["binding_key"]).business_id == (
        "Private Acme Electrical"
    )

    habit_repository = HabitCapsuleRepository(
        domain_store=store,
        workspace_id="acme",
    )
    promotion = HabitPromotionEngine(
        repository=habit_repository,
        domain_store=store,
        workspace_id="acme",
    ).evaluate_and_promote(
        capsule=private,
        run_evidence=[
            {"run_id": f"private-run-{i}", "run_ok": True, "quality": 0.94}
            for i in range(3)
        ],
        cau_state={"allow_learn": True, "adr_active": False},
    )
    assert promotion["promoted"] is True
    assert promotion["habit_path"].startswith(
        "vault://train_agent.automations/workflow_capsule_habits/"
    )
    habit_key = promotion["habit_key"]
    assert HabitCapsuleRepository(
        domain_store=store,
        workspace_id="acme",
    ).require(habit_key).source_workflow_key == private.canonical_key

    registry = HabitCapsuleRegistry(repository=habit_repository)
    rebuilt = registry.rebuild_and_save()
    assert rebuilt["saved"]["derived_registry_persisted"] is False
    assert registry.resolve_source_workflow_key(habit_key) == private.canonical_key

    feedback = WorkflowCapsuleFeedbackEngine(
        domain_store=store,
        workspace_id="acme",
        capsule_repository=repository,
    ).apply(
        capsule=private,
        run_result={
            "run_id": "private-run-feedback",
            "ok": True,
            "steps": [
                {"status": "simulated"},
                {"status": "simulated"},
            ],
        },
        cau_state={"allow_learn": True, "adr_active": False},
        persist_capsule=True,
    )
    assert feedback["path"].startswith(
        "vault://train_agent.runs_and_audit/workflow_capsule_feedback/"
    )
    assert feedback["mutation_applied"] is True
    assert feedback["learning_event"]["reason"] == (
        "guardian_feedback_record_is_authoritative"
    )
    assert repository.require(
        private.canonical_key,
        workspace_id="acme",
    ).resonance["sqi_score"] > 0
    assert not (tmp_path / ".runtime" / "workflow_capsules").exists()

    records = store.list("train_agent.automations", workspace_id="acme")
    entity_ids = {str(record["entity_id"]) for record in records}
    assert any("workflow_capsule_workspace_capsules/" in item for item in entity_ids)
    assert any("workflow_capsule_habits/" in item for item in entity_ids)
    assert any("workflow_capsule_local_bindings/" in item for item in entity_ids)
    audit_records = store.list("train_agent.runs_and_audit", workspace_id="acme")
    assert any(
        "workflow_capsule_habit_promotion_events/" in str(record["entity_id"])
        for record in audit_records
    )
    assert any(
        "workflow_capsule_feedback/" in str(record["entity_id"])
        for record in audit_records
    )
    assert store.guardian.verify_audit_chain()["healthy"] is True

    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Client" not in database_bytes
    assert b"private@example.test" not in database_bytes
    assert b"founder's private instructions" not in database_bytes
    assert b"Private Acme Electrical" not in database_bytes
