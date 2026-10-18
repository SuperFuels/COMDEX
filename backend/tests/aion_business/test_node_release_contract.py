from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
    department_vault_namespaces,
)
from backend.modules.aion_business.runtime.node_capabilities import classify_node
from backend.modules.aion_business.runtime.node_release_contract import (
    NODE_RELEASE_SCHEMA,
    ReleaseContractError,
    evaluate_release_preflight,
    evaluate_release_preflight_with_qualification,
    release_change_inventory_digest,
    validate_release_manifest,
)
from backend.modules.aion_business.runtime.node_platform_qualification import (
    REQUIRED_QUALIFICATION_CASES,
    build_node_platform_qualification,
    node_platform_qualification_envelope_sha256,
    sign_node_platform_qualification,
)


def _seal_change_inventory(payload):
    inventory = payload["release_change_inventory"]
    inventory["sha256"] = release_change_inventory_digest(
        feature_ids=inventory["feature_ids"],
        department_ids=inventory["department_ids"],
    )
    return payload


def manifest():
    return _seal_change_inventory({
        "schema_version": NODE_RELEASE_SCHEMA,
        "version": "1.2.0",
        "channel": "stable",
        "release_stage": "internal-preview",
        "customer_data_included": False,
        "customer_credentials_included": False,
        "targets": [
            {
                "target_id": "windows-x64",
                "system": "windows",
                "architectures": ["x86_64"],
                "artifact_bytes": 100_000_000,
                "sha256": "a" * 64,
            }
        ],
        "guardian_api_versions": ["guardian.v1"],
        "readable_vault_schemas": ["tessaris.business-vault.v1"],
        "health_gates": ["guardian", "critical_workflows", "receipt_chain"],
        "rollback_target": "1.1.0",
        "business_data_discovery": {
            "schema_version": "tessaris.business-data-release-evidence.v3",
            "manifest_sha256": "b" * 64,
            "scenario_catalogue_sha256": "d" * 64,
            "report_sha256": "c" * 64,
            "unknown_write_count": 0,
            "blocking_touchpoint_count": 0,
            "incomplete_discovery_session_count": 0,
            "required_discovery_session_count": 7,
            "runtime_trace_session_count": 7,
            "runtime_trace_scenarios": [
                "onboarding-to-boardroom", "business-and-department-maps",
                "pilot-conversations", "file-cabinet", "train-agent",
                "migration", "backup-recovery",
            ],
            "runtime_trace_sha256": {
                "business-onboarding": "1" * 64,
                "files-documents": "2" * 64,
                "automations-schedules": "3" * 64,
                "boardroom-business-maps": "4" * 64,
                "aion-pilot-conversations": "5" * 64,
                "import-export-migration": "6" * 64,
                "backup-recovery": "7" * 64,
            },
            "runtime_trace_surface_counts": {
                "business-onboarding": 2,
                "files-documents": 3,
                "automations-schedules": 2,
                "boardroom-business-maps": 2,
                "aion-pilot-conversations": 2,
                "import-export-migration": 3,
                "backup-recovery": 2,
            },
            "runtime_trace_domain_counts": {
                "business-onboarding": 8,
                "files-documents": 6,
                "automations-schedules": 4,
                "boardroom-business-maps": 5,
                "aion-pilot-conversations": 3,
                "import-export-migration": 8,
                "backup-recovery": 8,
            },
            "runtime_trace_external_class_counts": {
                "business-onboarding": 1,
                "files-documents": 0,
                "automations-schedules": 0,
                "boardroom-business-maps": 0,
                "aion-pilot-conversations": 0,
                "import-export-migration": 1,
                "backup-recovery": 2,
            },
        },
        "business_data_domains": [
            "business.identity",
            "business.structure",
            "business.map",
            "business.map_governance",
            "business.notes",
            "business.working_state",
            "business.knowledge",
            "business.knowledge_files",
            "business.knowledge_audit",
            "security.records",
            "security.audit",
            "work_schedule.records",
            "work_schedule.files",
            "support.records",
            "support.files",
            "sales.records",
            "sales.files",
            "sales.audit",
            "sales.completion_records",
            "finance.sales_records",
            "finance.bookkeeping_records",
            "finance.bookkeeping_journal",
            "finance.recurring_records",
            "finance.reconciliation_records",
            "finance.ledger_records",
            "finance.integration_records",
            "finance.operations_records",
            "finance.inbox_files",
            "departments.map",
            "departments.intelligence",
            "departments.operational_records",
            "departments.operational_audit",
            "departments.pilot_tasks",
            "departments.pilot_audit",
            "onboarding.foundation_session",
            "onboarding.receipts",
            "provider.model_selections",
            "train_agent.automations",
            "train_agent.runs_and_audit",
            "learning.customer_state",
            "learning.audit",
            "file_cabinet.tree",
            "file_cabinet.originals",
            "file_cabinet.governance",
            "vault.migration_receipts",
        ],
        "introduced_department_ids": [],
        "feature_data_changes": [],
        "release_change_inventory": {
            "schema_version": "tessaris.release-change-inventory.v1",
            "sha256": "",
            "feature_ids": [],
            "department_ids": [],
        },
    })


def windows_node():
    return classify_node(
        system="Windows", architecture="AMD64", os_release="11",
        cpu_logical_count=8, memory_bytes=16 * 1024**3,
        available_storage_bytes=100 * 1024**3,
    )


def test_compatible_signed_release_is_eligible():
    result = evaluate_release_preflight(
        manifest(), windows_node(), current_version="1.1.0",
        guardian_api_version="guardian.v1",
        vault_schema_version="tessaris.business-vault.v1",
        signature_verified=True, repository_metadata_fresh=True,
    )
    assert result.eligible is True
    assert result.target_id == "windows-x64"


def test_preflight_collects_all_fail_closed_reasons():
    result = evaluate_release_preflight(
        manifest(), windows_node(), current_version="1.2.0",
        guardian_api_version="guardian.v2", vault_schema_version="unknown",
        signature_verified=False, repository_metadata_fresh=False,
        available_storage_bytes=1,
    )
    assert result.eligible is False
    assert set(result.reasons) == {
        "guardian_api_incompatible",
        "release_not_newer_than_installed",
        "release_repository_metadata_stale",
        "release_signature_unverified",
        "release_storage_insufficient",
        "vault_schema_incompatible",
    }


def test_manifest_cannot_carry_customer_data_or_credentials():
    invalid = manifest()
    invalid["customer_data_included"] = True
    with pytest.raises(ReleaseContractError, match="customer_data_boundary_invalid"):
        validate_release_manifest(invalid)


def test_production_release_requires_exact_platform_qualification():
    candidate = manifest()
    candidate["release_stage"] = "production-candidate"
    with pytest.raises(ReleaseContractError, match="target_qualification_missing"):
        validate_release_manifest(candidate)
    candidate["targets"][0]["qualification_report_sha256"] = "e" * 64
    result = evaluate_release_preflight(
        candidate, windows_node(), current_version="1.1.0",
        guardian_api_version="guardian.v1",
        vault_schema_version="tessaris.business-vault.v1",
        signature_verified=True, repository_metadata_fresh=True,
    )
    assert result.eligible is False
    assert "release_platform_qualification_unverified" in result.reasons
    verified = evaluate_release_preflight(
        candidate, windows_node(), current_version="1.1.0",
        guardian_api_version="guardian.v1",
        vault_schema_version="tessaris.business-vault.v1",
        signature_verified=True, repository_metadata_fresh=True,
        platform_qualification_verified=True,
    )
    assert verified.eligible is True


def test_production_preflight_verifies_signed_report_instead_of_trusting_flag():
    candidate = manifest()
    candidate["release_stage"] = "production"
    key = Ed25519PrivateKey.generate()
    report = build_node_platform_qualification(
        qualification_id="qual-windows-x64-release-120",
        release_version="1.2.0",
        target_id="windows-x64",
        artifact_sha256="a" * 64,
        artifact_bytes=100_000_000,
        declared_system="windows",
        declared_architecture="x86_64",
        observed_system="windows",
        observed_architecture="x86_64",
        profile="desktop",
        clean_machine=True,
        started_at="2026-10-17T18:00:00+00:00",
        completed_at="2026-10-17T19:00:00+00:00",
        qualified_by="release-lab-1",
        cases={
            case_id: {
                "status": "passed",
                "evidence_sha256": f"{index + 1:064x}",
                "note_code": "native-clean-machine-evidence",
            }
            for index, case_id in enumerate(REQUIRED_QUALIFICATION_CASES)
        },
        platform_trust={
            "artifact_signature_valid": True,
            "service_identity_separate": True,
            "native_credential_store_verified": True,
            "no_public_inbound_admin_port": True,
        },
        vault_boundary={
            "roots_separate": True,
            "updater_cannot_open_vault": True,
            "guardian_cannot_write_application": True,
            "restore_hashes_and_invariants_match": True,
        },
    )
    envelope = sign_node_platform_qualification(report, private_key=key)
    candidate["targets"][0][
        "qualification_report_sha256"
    ] = node_platform_qualification_envelope_sha256(envelope)
    result = evaluate_release_preflight_with_qualification(
        candidate,
        windows_node(),
        current_version="1.1.0",
        guardian_api_version="guardian.v1",
        vault_schema_version="tessaris.business-vault.v1",
        signature_verified=True,
        repository_metadata_fresh=True,
        qualification_envelope=envelope,
        qualification_public_key=key.public_key(),
    )
    assert result.eligible is True
    tampered = {**envelope, "signature": "invalid"}
    rejected = evaluate_release_preflight_with_qualification(
        candidate,
        windows_node(),
        current_version="1.1.0",
        guardian_api_version="guardian.v1",
        vault_schema_version="tessaris.business-vault.v1",
        signature_verified=True,
        repository_metadata_fresh=True,
        qualification_envelope=tampered,
        qualification_public_key=key.public_key(),
    )
    assert rejected.eligible is False
    assert "release_platform_qualification_unverified" in rejected.reasons


def test_release_rejects_unknown_writes_or_incomplete_discovery():
    invalid = manifest()
    invalid["business_data_discovery"]["unknown_write_count"] = 1
    with pytest.raises(ReleaseContractError, match="unknown_business_data_writes"):
        validate_release_manifest(invalid)

    invalid = manifest()
    invalid["business_data_discovery"]["blocking_touchpoint_count"] = 1
    with pytest.raises(ReleaseContractError, match="blocking_business_data_touchpoints"):
        validate_release_manifest(invalid)

    invalid = manifest()
    invalid["business_data_discovery"]["incomplete_discovery_session_count"] = 1
    with pytest.raises(ReleaseContractError, match="incomplete_business_data_discovery"):
        validate_release_manifest(invalid)

    invalid = manifest()
    invalid["business_data_discovery"]["runtime_trace_session_count"] = 2
    with pytest.raises(ReleaseContractError, match="runtime_trace_coverage_incomplete"):
        validate_release_manifest(invalid)

    invalid = manifest()
    invalid["business_data_discovery"].pop("scenario_catalogue_sha256")
    with pytest.raises(ReleaseContractError, match="scenario_catalogue_digest_invalid"):
        validate_release_manifest(invalid)

    invalid = manifest()
    invalid["business_data_discovery"]["runtime_trace_sha256"].pop("files-documents")
    with pytest.raises(ReleaseContractError, match="runtime_trace_digests_invalid"):
        validate_release_manifest(invalid)


def test_release_rejects_new_data_feature_without_vault_domain_contract():
    invalid = manifest()
    invalid["business_data_domains"].append("new_update.customer_workspace")
    with pytest.raises(ReleaseContractError, match="new_update.customer_workspace"):
        validate_release_manifest(invalid)


def test_release_rejects_omitting_any_existing_protected_domain():
    invalid = manifest()
    invalid["business_data_domains"].remove("file_cabinet.originals")
    with pytest.raises(ReleaseContractError, match="release_omits:file_cabinet.originals"):
        validate_release_manifest(invalid)


def test_release_rejects_omitting_mandatory_business_continuity_journey():
    invalid = manifest()
    invalid["business_data_discovery"]["runtime_trace_sha256"].pop(
        "boardroom-business-maps"
    )
    invalid["business_data_discovery"]["runtime_trace_surface_counts"].pop(
        "boardroom-business-maps"
    )
    invalid["business_data_discovery"]["runtime_trace_domain_counts"].pop(
        "boardroom-business-maps"
    )
    invalid["business_data_discovery"]["runtime_trace_external_class_counts"].pop(
        "boardroom-business-maps"
    )
    invalid["business_data_discovery"]["required_discovery_session_count"] = 6
    invalid["business_data_discovery"]["runtime_trace_session_count"] = 6
    with pytest.raises(ReleaseContractError, match="continuity_sessions_missing"):
        validate_release_manifest(invalid)


def test_release_rejects_missing_runtime_domain_coverage_counts():
    invalid = manifest()
    invalid["business_data_discovery"]["runtime_trace_domain_counts"].pop(
        "business-onboarding"
    )
    with pytest.raises(ReleaseContractError, match="runtime_trace_domains_invalid"):
        validate_release_manifest(invalid)


def test_release_rejects_missing_runtime_external_class_coverage_counts():
    invalid = manifest()
    invalid["business_data_discovery"]["runtime_trace_external_class_counts"].pop(
        "business-onboarding"
    )
    with pytest.raises(ReleaseContractError, match="external_classes_invalid"):
        validate_release_manifest(invalid)


def test_release_rejects_new_department_without_explicit_vault_artifacts():
    update = manifest()
    update["introduced_department_ids"] = ["procurement", "research_and_development"]
    update["release_change_inventory"]["department_ids"] = [
        "procurement", "research_and_development",
    ]
    _seal_change_inventory(update)
    with pytest.raises(ReleaseContractError, match="department_vault_contract_missing"):
        validate_release_manifest(update)


def test_release_can_add_new_department_with_complete_vault_contract():
    update = manifest()
    namespaces = department_vault_namespaces("procurement")
    department_domains = sorted(namespaces)
    update["introduced_department_ids"] = ["procurement"]
    update["release_change_inventory"]["department_ids"] = ["procurement"]
    update["release_change_inventory"]["feature_ids"] = ["department-procurement"]
    _seal_change_inventory(update)
    update["feature_data_changes"] = [
        {
            "feature_id": "department-procurement",
            "department_id": "procurement",
            "captures_business_data": True,
            "business_data_domains": department_domains,
            "migration_strategy": "new_empty_domain",
            "legacy_sources": [],
            "data_artifacts": [
                {
                    "artifact_id": domain.replace(".", "-"),
                    "domain_id": domain,
                    "storage_class": BusinessDataDomainRegistry().get(domain).storage_class,
                    "vault_namespace": namespaces[domain],
                }
                for domain in department_domains
            ],
        }
    ]
    validate_release_manifest(update)


def test_release_rejects_department_artifact_outside_its_own_namespace():
    update = manifest()
    department_domains = [
        "departments.map",
        "departments.intelligence",
        "departments.operational_records",
        "departments.operational_audit",
        "departments.pilot_tasks",
        "departments.pilot_audit",
        "train_agent.automations",
        "train_agent.runs_and_audit",
        "file_cabinet.tree",
        "file_cabinet.originals",
        "file_cabinet.governance",
    ]
    update["introduced_department_ids"] = ["procurement"]
    update["release_change_inventory"]["department_ids"] = ["procurement"]
    update["release_change_inventory"]["feature_ids"] = ["department-procurement"]
    _seal_change_inventory(update)
    update["feature_data_changes"] = [
        {
            "feature_id": "department-procurement",
            "department_id": "procurement",
            "captures_business_data": True,
            "business_data_domains": department_domains,
            "migration_strategy": "new_empty_domain",
            "legacy_sources": [],
            "data_artifacts": [
                {
                    "artifact_id": domain.replace(".", "-"),
                    "domain_id": domain,
                    "storage_class": BusinessDataDomainRegistry().get(domain).storage_class,
                    "vault_namespace": (
                        "departments/sales/stolen-map"
                        if domain == "departments.map"
                        else f"departments/procurement/{domain}"
                    ),
                }
                for domain in department_domains
            ],
        }
    ]
    with pytest.raises(ReleaseContractError, match="department_vault_namespace_invalid"):
        validate_release_manifest(update)


def test_release_rejects_department_artifact_in_noncanonical_subdirectory():
    update = manifest()
    registry = BusinessDataDomainRegistry()
    namespaces = department_vault_namespaces("procurement")
    department_domains = sorted(namespaces)
    update["introduced_department_ids"] = ["procurement"]
    update["release_change_inventory"]["department_ids"] = ["procurement"]
    update["release_change_inventory"]["feature_ids"] = ["department-procurement"]
    _seal_change_inventory(update)
    update["feature_data_changes"] = [
        {
            "feature_id": "department-procurement",
            "department_id": "procurement",
            "captures_business_data": True,
            "business_data_domains": department_domains,
            "migration_strategy": "new_empty_domain",
            "legacy_sources": [],
            "data_artifacts": [
                {
                    "artifact_id": domain.replace(".", "-"),
                    "domain_id": domain,
                    "storage_class": registry.get(domain).storage_class,
                    "vault_namespace": (
                        "departments/procurement/maps/somewhere-else"
                        if domain == "departments.map"
                        else namespaces[domain]
                    ),
                }
                for domain in department_domains
            ],
        }
    ]
    with pytest.raises(
        ReleaseContractError,
        match="department_vault_namespace_noncanonical:procurement:departments.map",
    ):
        validate_release_manifest(update)


def test_release_rejects_unsafe_or_duplicate_vault_namespace():
    update = manifest()
    update["feature_data_changes"] = [
        {
            "feature_id": "new-customer-workspace",
            "captures_business_data": True,
            "business_data_domains": ["business.notes"],
            "migration_strategy": "new_empty_domain",
            "legacy_sources": [],
            "data_artifacts": [
                {
                    "artifact_id": "notes",
                    "domain_id": "business.notes",
                    "storage_class": "authoritative_record",
                    "vault_namespace": "../outside-the-vault",
                }
            ],
        }
    ]
    with pytest.raises(ReleaseContractError, match="vault_namespace_invalid"):
        validate_release_manifest(update)


def test_release_rejects_data_feature_that_omits_its_vault_domains():
    update = manifest()
    update["feature_data_changes"] = [
        {
            "feature_id": "new-customer-workspace",
            "captures_business_data": True,
            "business_data_domains": [],
            "migration_strategy": "copy_verify_switch",
            "legacy_sources": ["legacy/new-customer-workspace"],
            "data_artifacts": [],
        }
    ]
    with pytest.raises(ReleaseContractError, match="business_data_domains_missing"):
        validate_release_manifest(update)


def test_release_accepts_feature_bound_to_registered_vault_domain_and_migration():
    update = manifest()
    update["release_change_inventory"]["feature_ids"] = [
        "department-map-editor", "non-persistent-help-panel",
    ]
    _seal_change_inventory(update)
    update["feature_data_changes"] = [
        {
            "feature_id": "department-map-editor",
            "captures_business_data": True,
            "business_data_domains": ["departments.map", "departments.intelligence"],
            "migration_strategy": "copy_verify_switch",
            "legacy_sources": ["legacy/department-map.json"],
            "data_artifacts": [
                {
                    "artifact_id": "department-map",
                    "domain_id": "departments.map",
                    "storage_class": "authoritative_record",
                    "vault_namespace": "departments/{department_id}/map",
                },
                {
                    "artifact_id": "department-intelligence",
                    "domain_id": "departments.intelligence",
                    "storage_class": "authoritative_record",
                    "vault_namespace": "departments/{department_id}/intelligence",
                },
            ],
        },
        {
            "feature_id": "non-persistent-help-panel",
            "captures_business_data": False,
            "business_data_domains": [],
            "migration_strategy": "not_required",
            "legacy_sources": [],
            "data_artifacts": [],
        },
    ]
    validate_release_manifest(update)


def test_release_rejects_feature_missing_from_signed_change_inventory():
    update = manifest()
    update["feature_data_changes"] = [
        {
            "feature_id": "non-persistent-help-panel",
            "captures_business_data": False,
            "business_data_domains": [],
            "migration_strategy": "not_required",
            "legacy_sources": [],
            "data_artifacts": [],
        }
    ]
    with pytest.raises(ReleaseContractError, match="change_inventory_feature_mismatch"):
        validate_release_manifest(update)


def test_release_rejects_inventoried_feature_without_data_classification():
    update = manifest()
    update["release_change_inventory"]["feature_ids"] = ["unclassified-new-feature"]
    _seal_change_inventory(update)
    with pytest.raises(ReleaseContractError, match="change_inventory_feature_mismatch"):
        validate_release_manifest(update)


def test_release_rejects_introduced_department_missing_from_change_inventory():
    update = manifest()
    update["introduced_department_ids"] = ["procurement"]
    with pytest.raises(ReleaseContractError, match="change_inventory_department_mismatch"):
        validate_release_manifest(update)


def test_release_rejects_change_inventory_digest_that_does_not_match_lists():
    update = manifest()
    update["release_change_inventory"]["sha256"] = "f" * 64
    with pytest.raises(ReleaseContractError, match="change_inventory_digest_mismatch"):
        validate_release_manifest(update)
