from __future__ import annotations

import json

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.business_vault_coverage_migration import (
    BusinessVaultCoverageMigration,
)
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.modules.glyphnet.thread_logger import GlyphThreadStore
from backend.modules.aion_knowledge.knowledge_graph_core import AionKnowledgeGraphStore


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_coverage_migration_moves_named_surfaces_without_deleting_sources(tmp_path):
    legacy = tmp_path / ".runtime" / "AION_BUSINESS"
    workflow_capsules = tmp_path / ".runtime" / "workflow_capsules"
    aion_learning = tmp_path / ".runtime" / "COMDEX_MOVE" / "data"
    _write_json(
        legacy / "business_containers" / "acme" / "business_map.json",
        {"workspace_id": "acme", "kind": "business_map", "private": "strategy"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "department_intelligence.json",
        {"workspace_id": "acme", "kind": "department_intelligence", "departments": {"future_department": {"plan": "private"}}},
    )
    brand_asset = (
        legacy / "business_containers" / "acme" / "brand_assets"
        / "brand_primary_logo_0123456789abcdef.png"
    )
    brand_asset.parent.mkdir(parents=True, exist_ok=True)
    brand_asset.write_bytes(b"private legacy brand asset")
    _write_json(
        legacy / "foundation_onboarding" / "acme.json",
        {"schema_version": "aion.business_foundation_onboarding_session.v1", "workspace_id": "acme", "revision": 1, "packet": {"founder": "private"}},
    )
    _write_json(
        legacy / "department_pilot_runtime" / "acme" / "future_department" / "tasks" / "task-1.json",
        {"task": {"task_id": "task-1"}, "private": "department work"},
    )
    _write_json(
        legacy / "department_pilot_runtime" / "acme" / "finance" / "conversations" / "finance_terminal.json",
        {"workspace_id": "acme", "turns": [{"content": "private finance conversation"}]},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "pilot" / "operating_team"
        / "capsules" / "automation_only_department.json",
        {
            "workspace_id": "acme",
            "department_id": "automation_only_department",
            "private": "trained department state",
        },
    )
    _write_json(
        legacy / "external_specialists" / "acme" / "legal-reviewer.json",
        {
            "id": "legal-reviewer", "workspace_id": "acme", "name": "Private Reviewer",
            "specialist_type": "human_specialist", "provider": "private-network",
            "capabilities": ["legal_review"],
        },
    )
    _write_json(
        legacy / "external_work_orders" / "acme" / "work-private.json",
        {
            "id": "work-private", "workspace_id": "acme", "capability": "legal_review",
            "objective": "Review private agreement", "status": "queued",
        },
    )
    _write_json(
        legacy / "business_containers" / "acme" / "project_management.json",
        {
            "schema_version": "aion.project-management.v1", "revision": 1,
            "projects": [{"id": "project-private", "title": "Private expansion"}],
            "agent_drafts": {},
        },
    )
    _write_json(
        legacy / "founder_review_triggers" / "acme.json",
        {
            "workspace_id": "acme", "role_id": "ceo-core", "enabled": True,
            "cadence": "weekly", "days_back": 7, "include_draft": True,
            "send_email": True, "send_to_emails": ["founder@private.test"],
            "from_email": "review@private.test", "last_run_at": None,
            "metadata": {"private": "founder automation"},
        },
    )
    for stem in (
        "corrections", "verified_outcomes", "customer_change_log", "route_preferences",
        "automation_proposals", "curated_datasets", "model_releases",
    ):
        _write_json(
            legacy / "governed_improvement" / "acme" / f"{stem}.json",
            {"records": [{"id": f"private-{stem}", "private": "learned business state"}]},
        )
    _write_json(
        legacy / "signed_model_catalogue" / "acme" / "model_catalogue.json",
        {"schema_version": "aion.model_catalogue.v1", "models": {}, "routes": {"private": {"champion": "model@1"}}},
    )
    _write_json(
        legacy / "signed_model_catalogue" / "acme" / "customer_private_outcomes.json",
        {"schema_version": "aion.customer_private_model_outcomes.v1", "outcomes": [{"customer_id": "private-customer"}]},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "integrations" / "sales_telephony.json",
        {"twilio": {"validated": True, "phone_number": "+34950000000"}},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "medium_business" / "medium_business_operating_model.json",
        {"schema_version": "aion.medium_business_operating_model.v1", "revision": 1, "group": {"name": "Private Group"}},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "medium_business" / "medium_business_audit.json",
        {"events": [{"event": "configuration_changed", "actor": "private-founder"}]},
    )
    runtime_audit = legacy / "audit" / "acme" / "events.jsonl"
    runtime_audit.parent.mkdir(parents=True, exist_ok=True)
    runtime_audit.write_text(
        json.dumps({"id": "audit-private", "summary": "private runtime decision"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        legacy / "workspaces" / "acme.json",
        {"id": "acme", "name": "Private Workspace", "business_type": "services", "owner": "private-founder"},
    )
    _write_json(
        legacy / "topologies" / "acme.json",
        {"workspace_id": "acme", "nodes": [], "edges": [], "private": "operating topology"},
    )
    _write_json(
        legacy / "container_bindings" / "acme" / "customers.json",
        {
            "id": "customers", "workspace_id": "acme", "name": "Private Customers",
            "runtime_container_id": "container-private",
        },
    )
    for feature_id in ("agents", "roles", "tasks", "learning"):
        _write_json(
            legacy / feature_id / "acme" / f"{feature_id}-private.json",
            {"id": f"{feature_id}-private", "workspace_id": "acme", "private": f"private {feature_id}"},
        )
    _write_json(
        aion_learning / "logs" / "phase0_learning_memory.json",
        {
            "concepts": {
                "private-pricing": {
                    "corrected_response": "Never expose the customer's cost price"
                }
            }
        },
    )
    _write_json(
        aion_learning / "learning" / "aion_weakness_signals.json",
        {
            "signals": [
                {"weakness_id": "private-weakness", "skill_id": "private.customer.quote"}
            ]
        },
    )
    learning_events = aion_learning / "learning" / "aion_learning_events.jsonl"
    learning_events.parent.mkdir(parents=True, exist_ok=True)
    learning_events.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "event_id": "learning-private-1",
                    "event_type": "skill_run",
                    "timestamp": 1.0,
                    "private": "first customer learning event",
                },
                {
                    "event_id": "learning-private-2",
                    "event_type": "skill_run",
                    "timestamp": 2.0,
                    "private": "second customer learning event",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        aion_learning / "trading" / "decision_influence_weights.json",
        {
            "schema_version": "aion.decision_influence_weights.v2",
            "version": 3,
            "updated_at": "2026-10-17T00:00:00+00:00",
            "state": {"llm_trust_weights": {"private-route": 1.2}},
        },
    )
    decision_audit = aion_learning / "trading" / "decision_influence_audit.jsonl"
    decision_audit.parent.mkdir(parents=True, exist_ok=True)
    decision_audit.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "audit_id": "private-decision-audit-1",
                    "ts_utc": "2026-10-17T00:00:00+00:00",
                    "private": "first decision correction",
                },
                {
                    "audit_id": "private-decision-audit-2",
                    "ts_utc": "2026-10-17T00:01:00+00:00",
                    "private": "second decision correction",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        aion_learning / "predictive" / "resonance_state.json",
        {"avg_strength": 0.42, "decay_rate": 0.91, "update_count": 25},
    )
    resonance_log = aion_learning / "analysis" / "resonance_delta.jsonl"
    resonance_log.parent.mkdir(parents=True, exist_ok=True)
    resonance_log.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"timestamp": 3.0, "predicted_vec": [1.0], "actual_vec": [1.1]},
                {"timestamp": 4.0, "predicted_vec": [2.0], "actual_vec": [2.2]},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    llm_accuracy_log = aion_learning / "trading" / "llm_accuracy_log.jsonl"
    llm_accuracy_log.parent.mkdir(parents=True, exist_ok=True)
    llm_accuracy_log.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "record_type": "llm_accuracy",
                    "ts": 5.0,
                    "llm_id": "private-model-a",
                    "metadata": {"customer": "private-a"},
                },
                {
                    "record_type": "llm_accuracy",
                    "ts": 6.0,
                    "llm_id": "private-model-b",
                    "metadata": {"customer": "private-b"},
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    temporal_buffer = aion_learning / "predictive" / "temporal_buffer.json"
    temporal_buffer.parent.mkdir(parents=True, exist_ok=True)
    temporal_buffer.write_text(
        "\n".join(
            json.dumps({"triplet": row})
            for row in (["PRIVATE-A", "PRIVATE-B", "PRIVATE-C"], ["PRIVATE-B", "PRIVATE-C", "PRIVATE-D"])
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        aion_learning / "prediction" / "temporal_model.json",
        {
            "markov_graph": {"PRIVATE-C": {"PRIVATE-D": 2.0}},
            "confidence": 0.77,
        },
    )
    _write_json(
        aion_learning / "predictive" / "predictive_bias_state.json",
        {
            "window_size": 5,
            "transitions": {"PRIVATE-C->PRIVATE-D": 1.3},
            "counts": {"PRIVATE-C->PRIVATE-D": 2},
            "confidence": 0.81,
        },
    )
    predictive_log = aion_learning / "predictive" / "predictive_transitions.jsonl"
    predictive_log.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "event_type": "predictive_transition",
                    "timestamp": 7.0,
                    "prev": "PRIVATE-C",
                    "next": "PRIVATE-D",
                },
                {
                    "event_type": "predictive_evaluation",
                    "timestamp": 8.0,
                    "predicted": "PRIVATE-D",
                    "actual": "PRIVATE-D",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        legacy / "business_containers" / "acme" / "pilot" / "operating_team" / "routines" / "routine-1.json",
        {"routine_id": "routine-1", "instruction": "private automation"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "pilot" / "scheduled_work" / "schedules.json",
        {"workspace_id": "acme", "schedules": [{"title": "private scheduled automation"}]},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "pilot" / "scheduled_work" / "runs" / "run-private.json",
        {"run_id": "run-private", "private": "scheduled run result"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "pilot" / "scheduled_work" / "artifacts" / "artifact-private.json",
        {"artifact_id": "artifact-private", "private": "scheduled work artifact"},
    )
    _write_json(
        legacy / "aion_agents" / "workflow_definitions" / "acme" / "workflow-private.json",
        {"id": "workflow-private", "workspace_id": "acme", "department_key": "new_ventures", "private": "workflow definition"},
    )
    _write_json(
        legacy / "aion_agents" / "workflow_runs" / "acme" / "run-private.json",
        {"id": "run-private", "workspace_id": "acme", "department_id": "new_ventures", "private": "workflow run"},
    )
    _write_json(
        legacy / "aion_agents" / "approval_requests" / "acme" / "approval-private.json",
        {"id": "approval-private", "workspace_id": "acme", "department_id": "new_ventures", "private": "approval evidence"},
    )
    _write_json(
        legacy / "acme" / "aion_agents" / "agent_definitions" / "agent-private.json",
        {"id": "agent-private", "workspace_id": "acme", "department_id": "new_ventures", "private": "agent definition"},
    )
    _write_json(
        legacy / "acme" / "aion_agents" / "trigger_definitions" / "trigger-private.json",
        {"id": "trigger-private", "workspace_id": "acme", "department_id": "new_ventures", "private": "trigger definition"},
    )
    _write_json(
        legacy / "acme" / "aion_workflows" / "workflow-canvas-private.json",
        {
            "workflow_id": "workflow-canvas-private",
            "business_container": "acme",
            "department_id": "new_ventures",
            "name": "Private workflow canvas",
        },
    )
    _write_json(
        legacy / "acme" / "aion_workflow_approvals" / "workflow-canvas-private"
        / "approval-canvas-private.json",
        {
            "approval_id": "approval-canvas-private",
            "workflow_id": "workflow-canvas-private",
            "business_container": "acme",
            "status": "approved",
            "reason": "Private founder decision",
        },
    )
    workflow_audit = legacy / "acme" / "aion_workflow_audit" / "workflow-canvas-private.jsonl"
    workflow_audit.parent.mkdir(parents=True, exist_ok=True)
    workflow_audit.write_text(
        json.dumps({
            "mode": "dry_run", "workflow_id": "workflow-canvas-private",
            "business_container": "acme", "private": "dry-run evidence",
        }) + "\n" + json.dumps({
            "mode": "resume_after_approval_dry_run",
            "workflow_id": "workflow-canvas-private",
            "business_container": "acme", "private": "resume evidence",
        }) + "\n",
        encoding="utf-8",
    )
    _write_json(
        workflow_capsules / "glyph_store" / "items" / "MY-9001.v1.json",
        {
            "glyph_id": "glyph.my-9001",
            "glyph_code": "MY-9001",
            "glyph_version": "v1",
            "scope": "my",
            "name": "Private customer master glyph",
            "department_id": "new_ventures",
        },
    )
    _write_json(
        workflow_capsules / "glyph_store" / "items" / "UT-1001.v1.json",
        {
            "glyph_id": "glyph.ut-1001",
            "glyph_code": "UT-1001",
            "glyph_version": "v1",
            "scope": "universal",
            "name": "Replaceable signed product template",
        },
    )
    workspace_capsule = workflow_capsules / "workspace" / "acme" / "private.workflow.wiki.phn"
    workspace_capsule.parent.mkdir(parents=True, exist_ok=True)
    workspace_capsule.write_text(
        json.dumps({
            "canonical_key": "workflow:acme.private.customer.v1",
            "display_name": "Private customer capsule",
            "meaning": "Private Acme automation instructions",
            "department_id": "new_ventures",
        }),
        encoding="utf-8",
    )
    _write_json(
        workflow_capsules / "approvals" / "items" / "wf-appr-private.json",
        {
            "approval_id": "wf-appr-private",
            "run_id": "capsule-run-private",
            "canonical_key": "workflow:acme.private.customer.v1",
            "status": "approved",
            "private": "founder approval",
        },
    )
    capsule_approval_log = workflow_capsules / "approvals" / "workflow_approvals.jsonl"
    capsule_approval_log.write_text(
        json.dumps({
            "event_type": "approval_approved",
            "approval": {
                "approval_id": "wf-appr-private",
                "private": "approval event",
            },
        }) + "\n",
        encoding="utf-8",
    )
    capsule_run_log = workflow_capsules / "runs" / "workflow_execution_log.jsonl"
    capsule_run_log.parent.mkdir(parents=True, exist_ok=True)
    capsule_run_log.write_text(
        json.dumps({"run_id": "capsule-run-private", "private": "execution trace"}) + "\n",
        encoding="utf-8",
    )
    capsule_feedback_log = workflow_capsules / "feedback" / "workflow_capsule_feedback.jsonl"
    capsule_feedback_log.parent.mkdir(parents=True, exist_ok=True)
    capsule_feedback_log.write_text(
        json.dumps({"run_id": "capsule-run-private", "private": "learning feedback"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        workflow_capsules / "habits" / "habit_acme_private.json",
        {
            "habit_key": "habit:acme.private.customer.v1",
            "source_workflow_key": "workflow:acme.private.customer.v1",
            "display_name": "Private learned habit",
            "meaning": "Customer-specific learned routine",
        },
    )
    capsule_promotion_log = workflow_capsules / "habits" / "habit_promotion_log.jsonl"
    capsule_promotion_log.write_text(
        json.dumps({
            "source_workflow_key": "workflow:acme.private.customer.v1",
            "private": "habit promotion evidence",
        }) + "\n",
        encoding="utf-8",
    )
    _write_json(
        workflow_capsules / "habits" / "habit_capsule_registry.json",
        {"derived": "must not be migrated"},
    )
    _write_json(
        workflow_capsules / "local_bindings" / "private-binding.json",
        {
            "binding_key": "binding.acme.electrician.gmail_receptionist.v1",
            "workspace_id": "acme",
            "business_id": "private-acme-electrical",
            "pattern_key": "global.workflow.electrician.gmail_receptionist.v1",
            "workflow_canonical_key": "workflow:electrician.gmail_receptionist.v1",
            "connector_bindings": {"gmail": "connector.gmail.private"},
            "vault_bindings": {"gmail_credentials": "vault.gmail.credentials"},
            "business_context": {"private": "customer-specific binding"},
            "enabled": True,
        },
    )
    _write_json(
        legacy.parent / "aion_flow" / "runs" / "flow-run-private.json",
        {"run_id": "flow-run-private", "authority_context": {"workspace_id": "acme"}, "private": "flow run"},
    )
    _write_json(
        legacy.parent / "aion_flow" / "policies" / "acme.json",
        {"schema_version": "aion.flow.execution-policy.v1", "workspace_id": "acme", "revision": 2, "private": "automation policy"},
    )
    _write_json(
        legacy.parent / "aion_flow" / "evaluations" / "afexp_private.json",
        {
            "experiment_id": "afexp_private", "status": "collecting",
            "authority_context": {"workspace_id": "acme"}, "private": "evaluation evidence",
        },
    )
    _write_json(
        legacy.parent / "aion_flow" / "templates" / "organisation-installations.json",
        {
            "schema_version": "aion.flow.template_installations.v1",
            "installations": {
                "acme:governed-email-drafting": {
                    "installation_id": "acme:governed-email-drafting",
                    "organisation_id": "acme",
                    "active_template_ref": "governed-email-drafting@1.0.0",
                    "bindings": {"email_connector": "vault://private/email"},
                    "status": "installed_unapproved",
                },
                "other:not-ours": {
                    "installation_id": "other:not-ours", "organisation_id": "other",
                    "active_template_ref": "not-ours@1.0.0",
                },
            },
        },
    )
    _write_json(
        legacy.parent / "aion_flow" / "harnesses" / "acme" / "harnesses.json",
        {
            "schema_version": "aion.flow.harnesses.v1",
            "harnesses": {"private@1": {"private": "customer harness instructions"}},
            "routes": {"sales": {"active": "private@1", "history": []}},
        },
    )
    _write_json(
        legacy.parent / "aion_flow" / "capability_packages" / "acme" / "capability_packages.json",
        {
            "schema_version": "aion.capability_packages.v1",
            "packages": {"private@1": {"status": "active", "private": "customer qualification"}},
        },
    )
    _write_json(
        legacy.parent / "aion_flow" / "prepared" / "flow-prepared-private.json",
        {
            "preparation_id": "flow-prepared-private",
            "authorization_context": {"actor": {"workspace_id": "acme"}},
            "private": "prepared flow",
        },
    )
    _write_json(
        legacy.parent / "aion_flow" / "production" / "workflow-revisions.json",
        {
            "schema_version": "aion.flow.production_revisions.v1",
            "workflows": {
                "acme:private-production-flow": {
                    "revision": 1,
                    "history": [{
                        "workflow_id": "private-production-flow", "workspace_id": "acme",
                        "organisation_id": "acme", "revision": 1,
                        "graph": {"workflow_id": "private-production-flow", "private": "production automation"},
                    }],
                },
                "other:not-ours": {
                    "revision": 1,
                    "history": [{"workflow_id": "not-ours", "workspace_id": "other", "revision": 1}],
                },
            },
        },
    )
    knowledge_original = legacy / "business_containers" / "acme" / "business_knowledge" / "raw" / "source-private.txt"
    knowledge_original.parent.mkdir(parents=True, exist_ok=True)
    knowledge_original.write_bytes(b"private approved operating knowledge")
    _write_json(
        legacy / "business_containers" / "acme" / "business_knowledge" / "index.json",
        {
            "schema_version": "aion.business_knowledge.v1", "business_id": "acme", "revision": 1,
            "sources": [{
                "source_id": "source-private", "filename": "source-private.txt",
                "raw_local_path": str(knowledge_original), "created_at": "2026-10-17T00:00:00+00:00",
            }],
            "claims": [{"claim_id": "claim-private", "text": "private approved operating knowledge"}],
            "entity_links": [], "retrieval_receipts": [],
        },
    )
    knowledge_receipts = legacy / "business_containers" / "acme" / "business_knowledge" / "governance_receipts.jsonl"
    knowledge_receipts.write_text(
        json.dumps({"receipt_id": "knowledge-receipt-private", "action": "source_policy_updated"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        legacy / "cybersecurity_guard" / "acme" / "state.json",
        {"workspace_id": "acme", "assets": [{"display_name": "Private Finance Workstation"}]},
    )
    _write_json(
        legacy / "cybersecurity_guard" / "acme" / "vulnerability-feed.json",
        {"schema_version": "tessaris.cybersecurity.vulnerability-feed.v1", "entries": []},
    )
    security_events = legacy / "cybersecurity_guard" / "acme" / "events.jsonl"
    security_events.write_text(
        json.dumps({"event_id": "security-event-private", "event_type": "SAFE_SCAN_COMPLETED"}) + "\n",
        encoding="utf-8",
    )
    work_file = legacy / "business_containers" / "acme" / "work_schedule_files" / "work-1" / "quote.pdf"
    work_file.parent.mkdir(parents=True, exist_ok=True)
    work_file.write_bytes(b"private quotation PDF")
    _write_json(
        legacy / "business_containers" / "acme" / "work_schedule.json",
        {
            "schema_version": "aion.work-schedule.v3", "revision": 1,
            "items": [{
                "id": "work-1", "title": "Private customer work", "customer": "Alex",
                "documents": [{"id": "document-1", "name": "quote.pdf", "stored_name": "quote.pdf", "content_type": "application/pdf"}],
            }],
        },
    )
    support_file = legacy / "business_containers" / "acme" / "support" / "case_management" / "attachments" / "support-1.bin"
    support_file.parent.mkdir(parents=True, exist_ok=True)
    support_file.write_bytes(b"private support attachment")
    _write_json(
        legacy / "business_containers" / "acme" / "support" / "case_management" / "attachment_metadata" / "support-1.json",
        {"workspace_id": "acme", "attachment_id": "support-1", "protected_path": str(support_file)},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "support" / "voice" / "retell_deployment.json",
        {"workspace_id": "acme", "agent_id": "agent-private", "private": "voice deployment"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "support" / "voice" / "events" / "call-private.json",
        {"workspace_id": "acme", "call_id": "call-private", "private": "voice transcript"},
    )
    sales_file = legacy / "business_containers" / "acme" / "sales" / "revenue_spine" / "opportunity_attachments" / "opp-1" / "customer-file-1.pdf"
    sales_file.parent.mkdir(parents=True, exist_ok=True)
    sales_file.write_bytes(b"private sales attachment")
    _write_json(
        sales_file.with_suffix(".json"),
        {"workspace_id": "acme", "opportunity_id": "opp-1", "attachment_id": "customer-file-1"},
    )
    sales_audit = legacy / "business_containers" / "acme" / "sales" / "revenue_spine" / "audit.jsonl"
    sales_audit.write_text(json.dumps({"activity_id": "activity-1", "private": "sales event"}) + "\n", encoding="utf-8")
    _write_json(
        legacy / "business_containers" / "acme" / "sales" / "completion" / "quotes" / "quote-private.json",
        {"workspace_id": "acme", "quote_id": "quote-private", "private": "accepted terms"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "sales" / "invoices" / "invoice-private.json",
        {"workspace_id": "acme", "invoice_id": "invoice-private", "private": "customer invoice"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "bookkeeping" / "drafts" / "draft-private.json",
        {"workspace_id": "acme", "draft_id": "draft-private", "private": "journal draft"},
    )
    bookkeeping_journal = legacy / "business_containers" / "acme" / "finance" / "bookkeeping" / "internal_journal.jsonl"
    bookkeeping_journal.write_text(
        json.dumps({"workspace_id": "acme", "entry_id": "entry-private", "private": "posted journal"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "recurring" / "weekly-private" / "schedule.json",
        {"workspace_id": "acme", "schedule_id": "weekly-private", "private": "finance schedule"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "recurring" / "weekly-private" / "runs" / "run-private.json",
        {"workspace_id": "acme", "run_id": "run-private", "private": "finance run"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "transaction_reconciliations" / "reconcile-private.json",
        {"workspace_id": "acme", "run_id": "reconcile-private", "private": "bank matching"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "xero_reconciliation_handoffs" / "xero-private.json",
        {"workspace_id": "acme", "handoff_id": "xero-private", "private": "approved handoff"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "xero_reconciliation_handoffs" / "xero-private.blocked-receipt.json",
        {"workspace_id": "acme", "handoff_id": "xero-private", "private": "blocked receipt"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "xero_bookkeeping_exports" / "xero-export-private.json",
        {"workspace_id": "acme", "export_id": "xero-export-private", "private": "supplier bill export"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "xero_sales_invoice_exports" / "xero-sales-export-private.json",
        {"workspace_id": "acme", "export_id": "xero-sales-export-private", "private": "customer invoice export"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "ledger" / "ledger-private" / "ledger.json",
        {"workspace_id": "acme", "ledger_id": "ledger-private", "private": "ledger summary"},
    )
    ledger_collection = legacy / "business_containers" / "acme" / "finance" / "ledger" / "ledger-private" / "invoices.jsonl"
    ledger_collection.write_text(
        json.dumps({"invoice_id": "invoice-ledger-private", "private": "ledger customer"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        legacy / "business_containers" / "acme" / "integrations" / "xero" / "connection.json",
        {"status": "connected", "tenant_name": "Private Books"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "integrations" / "xero" / "syncs" / "sync-private" / "snapshot.json",
        {"sync_id": "sync-private", "private": "provider evidence"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "integrations" / "marketing" / "linkedin" / "connection.json",
        {"status": "connected", "provider": "linkedin", "private": "customer page selection"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "bank_activity" / "bank-private.json",
        {"record_id": "bank-private", "private": "bank activity"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "counterparty_intelligence" / "mappings.json",
        {"workspace_id": "acme", "private": "counterparty mapping"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "director_models" / "director-private.json",
        {"director_model_id": "director-private", "private": "director analysis"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "month_end" / "month-end-private.json",
        {"month_end_id": "month-end-private", "private": "month end review"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "scenarios" / "forecast-private.json",
        {"scenario_id": "forecast-private", "private": "customer forecast assumptions"},
    )
    _write_json(
        legacy / "business_containers" / "acme" / "finance" / "reports" / "report-private.json",
        {"report_id": "report-private", "private": "customer management report"},
    )
    finance_original = legacy / "business_containers" / "acme" / "finance" / "inbox" / "documents" / "finance-private" / "original.pdf"
    finance_original.parent.mkdir(parents=True, exist_ok=True)
    finance_original.write_bytes(b"private finance inbox original")
    _write_json(
        legacy / "business_containers" / "acme" / "finance_inbox.json",
        {
            "workspace_id": "acme", "kind": "finance_inbox", "documents": [{
                "id": "finance-private", "source": {
                    "filename": "private.pdf", "mime_type": "application/pdf",
                    "storage_path": str(finance_original), "received_at": "2026-10-17T00:00:00+00:00",
                },
            }],
        },
    )
    original = legacy / "business_containers" / "acme" / "files" / "customer.txt"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(b"private cabinet file")
    _write_json(
        legacy / "workflow_file_cabinets" / "acme" / "tree.json",
        {
            "workspace_id": "acme",
            "folders": [{"id": "file-1", "type": "artifact", "target": {"storage_path": str(original)}}],
            "metadata": {"updated_at": "2026-10-17T00:00:00+00:00"},
        },
    )

    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    key = b"m" * 32
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=key)
    store = VaultDomainStore(guardian)
    aion_resonance = tmp_path / "aion-resonance"
    _write_json(
        aion_resonance / "resonance_state.json",
        {
            "Φ_load": 0.42,
            "Φ_flux": 0.11,
            "Φ_entropy": 0.2,
            "Φ_coherence": 0.88,
            "last_command": "PRIVATE-CUSTOMER-COMMAND",
            "timestamp": 9.0,
        },
    )
    _write_json(
        aion_resonance / "boot_config.json",
        {
            "affirmative": {"\u03a6_coherence": 0.99},
            "PRIVATE-CUSTOMER-TERM": {"\u03a6_coherence": 0.73},
        },
    )
    aion_resonance_data = tmp_path / "aion-resonance-data"
    _write_json(
        aion_resonance_data / "conversation_memory.json",
        [
            {
                "timestamp": "2026-10-17T00:00:00",
                "command": "PRIVATE-CUSTOMER-CONVERSATION",
                "phi": {"Φ_coherence": 0.88, "Φ_entropy": 0.2},
                "reasoning": {"private": "customer reasoning"},
            }
        ],
    )
    _write_json(
        aion_resonance_data / "phi_reinforce_state.json",
        {
            "\u03a6_coherence": 0.91,
            "\u03a6_entropy": 0.2,
            "beliefs": {"trust": 0.88, "private": "customer belief state"},
        },
    )
    _write_json(
        aion_resonance_data / "phi_graph.json",
        {"nodes": {"PRIVATE-TERM": {"\u03a6_coherence": 0.9}}, "edges": {}},
    )
    _write_json(
        aion_resonance_data / "phi_trace.json",
        [{"timestamp": "2026-10-17T00:00:03+00:00", "last_command": "PRIVATE-TRACE"}],
    )
    _write_json(
        aion_resonance_data / "phi_drift_log.json",
        [{"timestamp": 1.0, "timestamp_readable": "2026-10-17T00:00:04+00:00", "keyword": "PRIVATE-DRIFT"}],
    )
    _write_json(
        aion_resonance_data / "symbolic_memory.json",
        [
            {
                "timestamp": "2026-10-17T00:00:01+00:00",
                "event": "reflect",
                "symbol": "⟲",
                "phi": {"Φ_coherence": 0.88},
                "belief": {"private": "customer symbolic belief"},
                "reflection": "PRIVATE-CUSTOMER-SYMBOLIC-REFLECTION",
            }
        ],
    )
    _write_json(
        aion_resonance_data / "symatic_log.json",
        [
            {
                "timestamp": "2026-10-17T00:00:02+00:00",
                "operator": "⟲",
                "equation": "PRIVATE-CUSTOMER-SYMATIC-EQUATION",
                "reflection": "customer equation reflection",
            }
        ],
    )
    reinforcement_history = (
        aion_resonance_data / "telemetry"
        / "private_engine_resonance_history.json"
    )
    _write_json(
        reinforcement_history,
        [
            {
                "timestamp": 10.0,
                "coherence": 0.91,
                "entropy": 0.09,
                "sqi": 0.91,
                "outcome": 0.8,
                "note": "PRIVATE-CUSTOMER-REINFORCEMENT-OUTCOME",
                "extras": {"private": "learned outcome"},
            }
        ],
    )
    pal_snapshot_log = aion_learning / "analysis" / "pal_snapshots.jsonl"
    pal_snapshot_log.write_text(
        json.dumps({
            "timestamp": "2026-10-17T00:00:03+00:00",
            "pal_summary": {"count": 1, "avg_reward": 0.8},
            "top_kg_links": [{
                "subject": "PRIVATE-PAL-SUBJECT",
                "predicate": "prefers",
                "object": "PRIVATE-PAL-OBJECT",
                "strength": 0.9,
            }],
        }) + "\n",
        encoding="utf-8",
    )
    aion_knowledge_db = tmp_path / "legacy-aion" / "aion_knowledge_graph.db"
    legacy_graph = AionKnowledgeGraphStore(
        legacy_db_path=aion_knowledge_db,
        auto_configure=False,
    )
    legacy_graph.put(
        "PRIVATE-KNOWLEDGE-SUBJECT",
        "prefers",
        "PRIVATE-KNOWLEDGE-OBJECT",
        vec=[0.2, 0.4],
        strength=0.7,
    )
    legacy_graph.put(
        "symbol:PRIVATE-KNOWLEDGE-SYMBOL",
        "is_a",
        "concept:PRIVATE-KNOWLEDGE-CONCEPT",
        strength=1.0,
    )
    concept_reinforcement_log = (
        tmp_path / "legacy-aion" / "concept_reinforcement.log"
    )
    concept_reinforcement_log.write_text(
        "13 reinforce PRIVATE-KNOWLEDGE-CONCEPT\n",
        encoding="utf-8",
    )
    concept_evolution_log = (
        tmp_path / "legacy-aion" / "concept_evolution_snapshot.jsonl"
    )
    concept_evolution_log.write_text(
        json.dumps({
            "timestamp": 14.0,
            "concepts": {"PRIVATE-KNOWLEDGE-CONCEPT": 1},
        }) + "\n",
        encoding="utf-8",
    )
    model_bindings_path = (
        tmp_path / "legacy-aion" / "model-bindings.json"
    )
    _write_json(
        model_bindings_path,
        {
            "schema_version": "aion.flow.model_bindings.v1",
            "bindings": {
                "private-primary": {
                    "binding_id": "private-primary",
                    "reference": "vault://model/private-primary",
                    "provider": "private",
                    "label": "PRIVATE-MODEL-BINDING-LABEL",
                    "vault_name": "model.private-primary.opaque-locator",
                    "status": "active",
                    "revision": 1,
                    "created_at": "2026-10-17T00:00:00+00:00",
                    "rotated_at": "",
                    "revoked_at": "",
                }
            },
        },
    )
    glyphnet_thread_db = tmp_path / "legacy-glyphnet" / "threadlog.sqlite"
    legacy_threads = GlyphThreadStore(legacy_db_path=glyphnet_thread_db)
    legacy_threads.append(
        "private-thread",
        {
            "graph": "work",
            "type": "text",
            "ts": 11.0,
            "from": "PRIVATE-GLYPHNET-SENDER",
            "to": "PRIVATE-GLYPHNET-RECIPIENT",
            "payload": {"text": "PRIVATE-GLYPHNET-MESSAGE"},
        },
        direction="in",
        user_id="private-user",
    )
    legacy_threads.append(
        "private-thread",
        {
            "graph": "work",
            "type": "voice",
            "ts": 12.0,
            "from": "PRIVATE-GLYPHNET-RECIPIENT",
            "to": "PRIVATE-GLYPHNET-SENDER",
            "payload": {"mime": "audio/webm", "bytes_b64": "PRIVATE-VOICE"},
        },
        user_id="private-user",
    )
    migration = BusinessVaultCoverageMigration(
        legacy_root=legacy,
        workflow_capsule_root=workflow_capsules,
        aion_learning_root=aion_learning,
        aion_resonance_root=aion_resonance,
        aion_resonance_data_root=aion_resonance_data,
        pal_snapshot_log_path=pal_snapshot_log,
        aion_knowledge_db_path=aion_knowledge_db,
        concept_reinforcement_log_path=concept_reinforcement_log,
        concept_evolution_log_path=concept_evolution_log,
        glyphnet_thread_db_path=glyphnet_thread_db,
        aion_flow_model_bindings_path=model_bindings_path,
        domain_store=store,
        object_store=VaultObjectStore(
            layout, guardian=guardian, business_stable_id="acme", encryption_key=key
        ),
        guardian_containers=GuardianBusinessContainerRepository(guardian),
    )

    dry_run = migration.migrate_workspace("acme", actor_id="founder", execute=False)
    assert dry_run["candidate_count"] == 137
    assert dry_run["authority_switch_allowed"] is False
    executed = migration.migrate_workspace("acme", actor_id="founder", execute=True)
    assert executed["verified_count"] == executed["candidate_count"] == 137
    assert executed["authority_switch_allowed"] is True
    assert executed["legacy_sources_deleted"] == 0
    assert executed["protected_surface_scan_complete"] is True
    assert executed["discovered_department_ids"] == [
        "automation_only_department", "finance", "future_department", "new_ventures",
    ]
    assert set(executed["department_vault_contracts"]["automation_only_department"]) == {
        "departments.map", "departments.intelligence",
        "departments.operational_records", "departments.operational_audit",
        "departments.pilot_tasks", "departments.pilot_audit",
        "train_agent.automations", "train_agent.runs_and_audit",
        "file_cabinet.tree", "file_cabinet.originals", "file_cabinet.governance",
    }
    future_contract = executed["department_vault_contracts"]["future_department"]
    assert future_contract["departments.map"].startswith(
        "departments/future_department/"
    )
    map_rows = {
        row["domain_id"]: row
        for row in executed["protected_surface_coverage"][
            "business_and_department_maps"
        ]
    }
    assert map_rows["business.map"]["source_state"] == "verified"
    assert map_rows["departments.map"]["source_state"] == "verified"
    assert executed["protected_surface_coverage"]["whole_file_cabinet"]
    assert original.read_bytes() == b"private cabinet file"

    business_map = migration.guardian_containers.load_dict("acme", "business_map")
    assert business_map["private"] == "strategy"
    department_map = migration.guardian_containers.load_dict("acme", "department_intelligence")
    assert department_map["departments"]["future_department"]["plan"] == "private"
    onboarding = store.get(
        "onboarding.foundation_session", workspace_id="acme", entity_id="foundation-session"
    )["payload"]
    assert onboarding["packet"]["founder"] == "private"
    assert store.get(
        "finance.operations_records", workspace_id="acme", entity_id="pilot/conversation"
    )["payload"]["turns"][0]["content"] == "private finance conversation"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="business_operations/external_specialists/legal-reviewer",
    )["payload"]["name"] == "Private Reviewer"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="business_operations/external_work_orders/work-private",
    )["payload"]["objective"] == "Review private agreement"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="projects/project_management/portfolio",
    )["payload"]["projects"][0]["title"] == "Private expansion"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="founder_review/triggers/config",
    )["payload"]["metadata"]["private"] == "founder automation"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="governed_improvement/corrections",
    )["payload"]["records"][0]["private"] == "learned business state"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="governed_improvement/model_releases",
    )["payload"]["records"][0]["private"] == "learned business state"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="model_catalogue/state",
    )["payload"]["routes"]["private"]["champion"] == "model@1"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="model_catalogue/customer_private_outcomes",
    )["payload"]["outcomes"][0]["customer_id"] == "private-customer"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="sales/integrations/telephony",
    )["payload"]["twilio"]["phone_number"] == "+34950000000"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="business_operations/medium_business_operating_model/model",
    )["payload"]["group"]["name"] == "Private Group"
    assert store.get(
        "departments.operational_audit", workspace_id="acme",
        entity_id="business_operations/medium_business_operating_model/legacy-event-00000001",
    )["payload"]["actor"] == "private-founder"
    assert store.get(
        "departments.operational_audit", workspace_id="acme",
        entity_id="business_operations/runtime_audit/events/audit-private",
    )["payload"]["summary"] == "private runtime decision"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="business_operations/workspaces/workspace",
    )["payload"]["name"] == "Private Workspace"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="business_operations/topologies/topology",
    )["payload"]["private"] == "operating topology"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="business_operations/container_bindings/customers",
    )["payload"]["name"] == "Private Customers"
    for feature_id in ("agents", "roles", "tasks", "learning"):
        assert store.get(
            "departments.operational_records", workspace_id="acme",
            entity_id=f"business_operations/{feature_id}/{feature_id}-private",
        )["payload"]["private"] == f"private {feature_id}"
    assert store.get(
        "learning.customer_state", workspace_id="acme", entity_id="teaching_memory",
    )["payload"]["concepts"]["private-pricing"]["corrected_response"] == (
        "Never expose the customer's cost price"
    )
    assert store.get(
        "learning.customer_state", workspace_id="acme", entity_id="weakness_signals",
    )["payload"]["signals"][0]["weakness_id"] == "private-weakness"
    assert [
        row["payload"]["private"]
        for row in sorted(
            (
                item
                for item in store.list("learning.audit", workspace_id="acme")
                if item["payload"].get("event_type") == "skill_run"
            ),
            key=lambda item: item["payload"]["timestamp"],
        )
    ] == [
        "first customer learning event",
        "second customer learning event",
    ]
    teaching_memory_path = aion_learning / "logs" / "phase0_learning_memory.json"
    assert teaching_memory_path.exists()
    assert learning_events.exists()
    assert store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="decision_influence_weights",
    )["payload"]["state"]["llm_trust_weights"]["private-route"] == 1.2
    decision_rows = sorted(
        (
            row
            for row in store.list("learning.audit", workspace_id="acme")
            if row["payload"].get("event_type") == "decision_influence_audit"
        ),
        key=lambda row: row["payload"]["ts_utc"],
    )
    assert [row["payload"]["private"] for row in decision_rows] == [
        "first decision correction",
        "second decision correction",
    ]
    assert decision_audit.exists()
    assert store.get(
        "learning.customer_state", workspace_id="acme", entity_id="resonance_state",
    )["payload"]["avg_strength"] == 0.42
    resonance_rows = sorted(
        (
            row
            for row in store.list("learning.audit", workspace_id="acme")
            if row["payload"].get("event_type") == "gradient_correction"
        ),
        key=lambda row: row["payload"]["timestamp"],
    )
    assert [row["payload"]["actual_vec"] for row in resonance_rows] == [[1.1], [2.2]]
    assert resonance_log.exists()
    llm_accuracy_rows = sorted(
        (
            row
            for row in store.list("learning.audit", workspace_id="acme")
            if row["payload"].get("record_type") == "llm_accuracy"
        ),
        key=lambda row: row["payload"]["ts"],
    )
    assert [row["payload"]["llm_id"] for row in llm_accuracy_rows] == [
        "private-model-a",
        "private-model-b",
    ]
    assert llm_accuracy_log.exists()
    assert store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="temporal_coherence_model",
    )["payload"]["markov_graph"]["PRIVATE-C"]["PRIVATE-D"] == 2.0
    assert store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="predictive_bias_state",
    )["payload"]["transitions"]["PRIVATE-C->PRIVATE-D"] == 1.3
    assert [
        row["payload"]["triplet"]
        for row in sorted(
            (
                row for row in store.list("learning.audit", workspace_id="acme")
                if row["payload"].get("event_type") == "temporal_sequence"
            ),
            key=lambda row: row["payload"]["vault_order_ns"],
        )
    ] == [
        ["PRIVATE-A", "PRIVATE-B", "PRIVATE-C"],
        ["PRIVATE-B", "PRIVATE-C", "PRIVATE-D"],
    ]
    prediction_rows = sorted(
        (
            row for row in store.list("learning.audit", workspace_id="acme")
            if row["payload"].get("event_type") in {
                "predictive_transition", "predictive_evaluation",
            }
        ),
        key=lambda row: row["payload"]["vault_order_ns"],
    )
    assert [row["payload"]["event_type"] for row in prediction_rows] == [
        "predictive_transition", "predictive_evaluation",
    ]
    assert temporal_buffer.exists()
    assert predictive_log.exists()
    assert store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="aion_phi_state",
    )["payload"]["last_command"] == "PRIVATE-CUSTOMER-COMMAND"
    assert (aion_resonance / "resonance_state.json").exists()
    lexicon_payload = store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="resonance_lexicon_overrides",
    )["payload"]
    assert lexicon_payload["overrides"]["PRIVATE-CUSTOMER-TERM"] == {
        "\u03a6_coherence": 0.73,
    }
    assert lexicon_payload["requires_baseline_review"] is True
    assert (aion_resonance / "boot_config.json").exists()
    assert store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="conversation_memory",
    )["payload"]["entries"][0]["command"] == "PRIVATE-CUSTOMER-CONVERSATION"
    assert (aion_resonance_data / "conversation_memory.json").exists()
    assert store.get(
        "learning.customer_state",
        workspace_id="acme",
        entity_id="phi_reinforce_state",
    )["payload"]["beliefs"]["trust"] == 0.88
    assert (aion_resonance_data / "phi_reinforce_state.json").exists()
    assert store.get(
        "learning.customer_state", workspace_id="acme",
        entity_id="phi_relationship_graph",
    )["payload"]["nodes"]["PRIVATE-TERM"]["\u03a6_coherence"] == 0.9
    learning_rows = [
        row["payload"] for row in store.list("learning.audit", workspace_id="acme")
    ]
    assert any(row.get("event_type") == "phi_learning_trace" for row in learning_rows)
    assert any(row.get("event_type") == "phi_drift" for row in learning_rows)
    assert (aion_resonance_data / "phi_graph.json").exists()
    assert (aion_resonance_data / "phi_trace.json").exists()
    assert (aion_resonance_data / "phi_drift_log.json").exists()
    symbolic_rows = store.list("learning.audit", workspace_id="acme")
    symbolic_rows = [
        row for row in symbolic_rows
        if row["payload"].get("event_type") == "symbolic_reflection"
    ]
    assert symbolic_rows[0]["payload"]["reflection"] == (
        "PRIVATE-CUSTOMER-SYMBOLIC-REFLECTION"
    )
    assert (aion_resonance_data / "symbolic_memory.json").exists()
    symatic_rows = store.list("learning.audit", workspace_id="acme")
    symatic_rows = [
        row for row in symatic_rows
        if row["payload"].get("event_type") == "symatic_equation"
    ]
    assert symatic_rows[0]["payload"]["equation"] == (
        "PRIVATE-CUSTOMER-SYMATIC-EQUATION"
    )
    assert (aion_resonance_data / "symatic_log.json").exists()
    reinforcement_rows = [
        row["payload"]
        for row in store.list("learning.audit", workspace_id="acme")
        if row["payload"].get("event_type")
        == "resonance_reinforcement_snapshot"
    ]
    assert reinforcement_rows[0]["engine_name"] == "private_engine"
    assert reinforcement_rows[0]["note"] == (
        "PRIVATE-CUSTOMER-REINFORCEMENT-OUTCOME"
    )
    assert reinforcement_history.exists()
    pal_rows = [
        row["payload"]
        for row in store.list("learning.audit", workspace_id="acme")
        if row["payload"].get("event_type") == "pal_learning_snapshot"
    ]
    assert pal_rows[0]["top_kg_links"][0]["subject"] == "PRIVATE-PAL-SUBJECT"
    assert pal_snapshot_log.exists()
    graph_rows = [
        row["payload"]
        for row in store.list("business.knowledge", workspace_id="acme")
        if row["payload"].get("record_type") == "aion_knowledge_triplet"
    ]
    assert {row["subject"] for row in graph_rows} == {
        "PRIVATE-KNOWLEDGE-SUBJECT",
        "symbol:PRIVATE-KNOWLEDGE-SYMBOL",
    }
    assert next(
        row for row in graph_rows if row["subject"] == "PRIVATE-KNOWLEDGE-SUBJECT"
    )["vec"] == [0.2, 0.4]
    assert aion_knowledge_db.exists()
    concept_audit_rows = [
        row["payload"]
        for row in store.list("learning.audit", workspace_id="acme")
        if row["payload"].get("event_type")
        in {"concept_reinforcement", "concept_evolution_snapshot"}
    ]
    assert {row["event_type"] for row in concept_audit_rows} == {
        "concept_reinforcement",
        "concept_evolution_snapshot",
    }
    assert concept_reinforcement_log.exists()
    assert concept_evolution_log.exists()
    migrated_binding = store.get(
        "train_agent.automations",
        workspace_id="acme",
        entity_id="aion_flow/model_binding/private-primary",
    )["payload"]
    assert migrated_binding["label"] == "PRIVATE-MODEL-BINDING-LABEL"
    assert migrated_binding["vault_name"] == (
        "model.private-primary.opaque-locator"
    )
    assert migrated_binding["legacy_source_retained"] is True
    assert model_bindings_path.exists()
    glyphnet_rows = sorted(
        (
            row["payload"]
            for row in store.list("business.knowledge_audit", workspace_id="acme")
            if row["payload"].get("record_type") == "glyphnet_thread_event"
        ),
        key=lambda row: row["ts"],
    )
    assert [row["type"] for row in glyphnet_rows] == ["text", "voice"]
    assert glyphnet_rows[0]["payload"]["text"] == "PRIVATE-GLYPHNET-MESSAGE"
    assert glyphnet_rows[1]["payload"]["bytes_b64"] == "PRIVATE-VOICE"
    assert glyphnet_thread_db.exists()

    tree = store.get("file_cabinet.tree", workspace_id="acme", entity_id="tree")["payload"]
    target = tree["folders"][0]["target"]
    assert "storage_path" not in target
    metadata, copied = migration.object_store.get_bytes(object_id=target["vault_object_id"])
    assert metadata["original_name"] == "customer.txt"
    assert copied == b"private cabinet file"
    brand_metadata, brand_copied = migration.object_store.get_bytes(
        object_id="brand_primary_logo_0123456789abcdef"
    )
    assert brand_metadata["content_type"] == "image/png"
    assert brand_copied == b"private legacy brand asset"
    assert brand_asset.read_bytes() == b"private legacy brand asset"
    assert len(store.list("train_agent.automations", workspace_id="acme")) == 24
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="legacy_aion_agents/workflow_definitions/workflow-private",
    )["payload"]["private"] == "workflow definition"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="legacy_aion_agents/agent_definitions/agent-private",
    )["payload"]["private"] == "agent definition"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="legacy_aion_agents/trigger_definitions/trigger-private",
    )["payload"]["private"] == "trigger definition"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="legacy_aion_agents/workflow_runs/run-private",
    )["payload"]["private"] == "workflow run"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="legacy_aion_agents/approval_requests/approval-private",
    )["payload"]["private"] == "approval evidence"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="legacy_aion_agents/workflow_glyphs/workflow-canvas-private",
    )["payload"]["name"] == "Private workflow canvas"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="legacy_aion_agents/workflow_approvals/approval-canvas-private",
    )["payload"]["reason"] == "Private founder decision"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_dry_runs/"
            "workflow-canvas-private/legacy-00000001"
        ),
    )["payload"]["private"] == "dry-run evidence"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_resume_runs/"
            "workflow-canvas-private/legacy-00000002"
        ),
    )["payload"]["private"] == "resume evidence"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_glyphs/MY-9001/v1"
        ),
    )["payload"]["name"] == "Private customer master glyph"
    assert not any(
        "UT-1001" in str(row.get("entity_id"))
        for row in store.list("train_agent.automations", workspace_id="acme")
    )
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_workspace_capsules/"
            "workflow_acme.private.customer.v1"
        ),
    )["payload"]["meaning"] == "Private Acme automation instructions"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_habits/"
            "habit:acme.private.customer.v1"
        ),
    )["payload"]["display_name"] == "Private learned habit"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_local_bindings/"
            "binding.acme.electrician.gmail_receptionist.v1"
        ),
    )["payload"]["business_context"]["private"] == "customer-specific binding"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_approvals/wf-appr-private"
        ),
    )["payload"]["private"] == "founder approval"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_traces/"
            "capsule-run-private-legacy-00000001"
        ),
    )["payload"]["private"] == "execution trace"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id=(
            "legacy_aion_agents/workflow_capsule_feedback/"
            "capsule-run-private-legacy-00000001"
        ),
    )["payload"]["private"] == "learning feedback"
    assert not any(
        "habit_capsule_registry" in str(row.get("entity_id"))
        for row in store.list("train_agent.automations", workspace_id="acme")
    )
    assert store.get(
        "train_agent.automations", workspace_id="acme", entity_id="scheduled_work/schedules"
    )["payload"]["schedules"][0]["title"] == "private scheduled automation"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="scheduled_work/runs/run-private",
    )["payload"]["private"] == "scheduled run result"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="scheduled_work/artifacts/artifact-private",
    )["payload"]["private"] == "scheduled work artifact"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="aion_flow/runs/flow-run-private",
    )["payload"]["private"] == "flow run"
    assert store.get(
        "train_agent.automations", workspace_id="acme", entity_id="aion_flow/policy",
    )["payload"]["private"] == "automation policy"
    assert store.get(
        "train_agent.runs_and_audit", workspace_id="acme",
        entity_id="aion_flow/evaluations/afexp_private",
    )["payload"]["private"] == "evaluation evidence"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="aion_flow/template_installations/acme:governed-email-drafting",
    )["payload"]["bindings"]["email_connector"] == "vault://private/email"
    assert store.get(
        "train_agent.automations", workspace_id="acme", entity_id="aion_flow/harnesses",
    )["payload"]["harnesses"]["private@1"]["private"] == "customer harness instructions"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="aion_flow/capability_packages",
    )["payload"]["packages"]["private@1"]["private"] == "customer qualification"
    assert store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="aion_flow/prepared/flow-prepared-private",
    )["payload"]["private"] == "prepared flow"
    revisions = store.get(
        "train_agent.automations", workspace_id="acme",
        entity_id="aion_flow/production_revisions",
    )["payload"]["workflows"]
    assert revisions["acme:private-production-flow"]["history"][0]["graph"]["private"] == "production automation"
    assert "other:not-ours" not in revisions
    knowledge = store.get("business.knowledge", workspace_id="acme", entity_id="index")["payload"]
    knowledge_source = knowledge["sources"][0]
    assert "raw_local_path" not in knowledge_source
    _, migrated_knowledge_file = migration.object_store.get_bytes(
        object_id=knowledge_source["vault_object_id"]
    )
    assert migrated_knowledge_file == b"private approved operating knowledge"
    assert store.get(
        "business.knowledge_audit", workspace_id="acme",
        entity_id="governance_receipts/knowledge-receipt-private",
    )["payload"]["action"] == "source_policy_updated"
    assert store.get(
        "security.records", workspace_id="acme", entity_id="guard/state"
    )["payload"]["assets"][0]["display_name"] == "Private Finance Workstation"
    assert store.get(
        "security.records", workspace_id="acme", entity_id="guard/vulnerability-feed"
    )["payload"]["entries"] == []
    assert store.get(
        "security.audit", workspace_id="acme", entity_id="events/security-event-private"
    )["payload"]["event_type"] == "SAFE_SCAN_COMPLETED"
    assert len(store.list("departments.pilot_tasks", workspace_id="acme")) == 1
    schedule = store.get("work_schedule.records", workspace_id="acme", entity_id="schedule")["payload"]
    work_document = schedule["items"][0]["documents"][0]
    assert work_document["vault_object_id"].startswith("workmig-")
    _, migrated_work_file = migration.object_store.get_bytes(object_id=work_document["vault_object_id"])
    assert migrated_work_file == b"private quotation PDF"
    support_record = store.get(
        "support.records", workspace_id="acme", entity_id="attachment_metadata/support-1"
    )["payload"]
    assert "protected_path" not in support_record
    _, migrated_support_file = migration.object_store.get_bytes(object_id=support_record["vault_object_id"])
    assert migrated_support_file == b"private support attachment"
    assert store.get(
        "support.records", workspace_id="acme", entity_id="voice/retell_deployment"
    )["payload"]["private"] == "voice deployment"
    assert store.get(
        "support.records", workspace_id="acme", entity_id="voice/events/call-private"
    )["payload"]["private"] == "voice transcript"
    sales_record = store.get(
        "sales.records", workspace_id="acme",
        entity_id="opportunity_attachments/opp-1/customer-file-1",
    )["payload"]
    _, migrated_sales_file = migration.object_store.get_bytes(object_id=sales_record["vault_object_id"])
    assert migrated_sales_file == b"private sales attachment"
    assert len(store.list("sales.audit", workspace_id="acme")) == 1
    completion = store.get(
        "sales.completion_records", workspace_id="acme", entity_id="quotes/quote-private"
    )["payload"]
    assert completion["private"] == "accepted terms"
    assert store.get(
        "finance.sales_records", workspace_id="acme", entity_id="invoices/invoice-private"
    )["payload"]["private"] == "customer invoice"
    assert store.get(
        "finance.bookkeeping_records", workspace_id="acme", entity_id="drafts/draft-private"
    )["payload"]["private"] == "journal draft"
    assert store.get(
        "finance.bookkeeping_journal", workspace_id="acme", entity_id="entry-private"
    )["payload"]["private"] == "posted journal"
    assert len(store.list("finance.recurring_records", workspace_id="acme")) == 2
    assert store.get(
        "finance.reconciliation_records", workspace_id="acme", entity_id="reconcile-private"
    )["payload"]["private"] == "bank matching"
    assert store.get(
        "finance.reconciliation_records", workspace_id="acme", entity_id="xero_handoffs/xero-private"
    )["payload"]["private"] == "approved handoff"
    assert store.get(
        "finance.reconciliation_records", workspace_id="acme",
        entity_id="xero_handoffs/xero-private/blocked_receipt",
    )["payload"]["private"] == "blocked receipt"
    assert store.get(
        "finance.integration_records", workspace_id="acme",
        entity_id="xero/bookkeeping_exports/xero-export-private",
    )["payload"]["private"] == "supplier bill export"
    assert store.get(
        "finance.integration_records", workspace_id="acme",
        entity_id="xero/sales_invoice_exports/xero-sales-export-private",
    )["payload"]["private"] == "customer invoice export"
    assert store.get(
        "finance.ledger_records", workspace_id="acme", entity_id="ledgers/ledger-private/ledger"
    )["payload"]["private"] == "ledger summary"
    assert store.get(
        "finance.ledger_records", workspace_id="acme",
        entity_id="ledgers/ledger-private/collections/invoices",
    )["payload"]["records"][0]["private"] == "ledger customer"
    assert store.get(
        "finance.integration_records", workspace_id="acme", entity_id="xero/connection"
    )["payload"]["tenant_name"] == "Private Books"
    assert store.get(
        "finance.integration_records", workspace_id="acme",
        entity_id="xero/syncs/sync-private/snapshot",
    )["payload"]["private"] == "provider evidence"
    assert store.get(
        "departments.operational_records", workspace_id="acme",
        entity_id="marketing/connections/linkedin/connection",
    )["payload"]["private"] == "customer page selection"
    assert store.get(
        "finance.operations_records", workspace_id="acme", entity_id="bank_activity/bank-private"
    )["payload"]["private"] == "bank activity"
    assert store.get(
        "finance.operations_records", workspace_id="acme",
        entity_id="counterparty_intelligence/mappings",
    )["payload"]["private"] == "counterparty mapping"
    assert store.get(
        "finance.operations_records", workspace_id="acme", entity_id="director_models/director-private"
    )["payload"]["private"] == "director analysis"
    assert store.get(
        "finance.operations_records", workspace_id="acme", entity_id="month_end/month-end-private"
    )["payload"]["private"] == "month end review"
    assert store.get(
        "finance.operations_records", workspace_id="acme", entity_id="scenarios/forecast-private"
    )["payload"]["private"] == "customer forecast assumptions"
    assert store.get(
        "finance.operations_records", workspace_id="acme", entity_id="reports/report-private"
    )["payload"]["private"] == "customer management report"
    migrated_inbox = migration.guardian_containers.load_dict("acme", "finance_inbox")
    migrated_source = migrated_inbox["documents"][0]["source"]
    assert "storage_path" not in migrated_source
    _, migrated_finance_original = migration.object_store.get_bytes(
        object_id=migrated_source["vault_object_id"]
    )
    assert migrated_finance_original == b"private finance inbox original"
    assert finance_original.read_bytes() == b"private finance inbox original"
    assert len(store.list("vault.migration_receipts", workspace_id="acme")) == 1
