"""Dependency-light smoke checks for the Vault, Node/update and Photon foundations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.modules.aion_business.runtime.business_data_discovery import (
    MANIFEST_SCHEMA,
    reconcile_scan,
    scan_repository,
)
from backend.modules.aion_business.runtime.business_vault import (
    VaultBoundaryError,
    provision_business_vault,
)
from backend.modules.aion_business.runtime.node_capabilities import classify_node
from backend.modules.aion_business.runtime.node_release_contract import (
    evaluate_release_preflight,
)
from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonLedger,
    PhotonLedgerEntry,
    PhotonPriceBook,
    PhotonWalletEngine,
    sign_price_book,
    verify_price_book,
)


class _SmokeSigner:
    public_key_b64 = "smoke-test-key"

    def sign(self, payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()


def _smoke_verify(key: str, payload: bytes, signature: str) -> bool:
    return key == "smoke-test-key" and hashlib.sha256(payload).hexdigest() == signature


def run() -> None:
    with TemporaryDirectory(prefix="tessaris-foundation-smoke-") as temporary:
        root = Path(temporary)
        (root / "backend").mkdir()
        (root / "backend" / "customer.py").write_text(
            "from pathlib import Path\nPath('customer.json').write_text('private')\n",
            encoding="utf-8",
        )
        scan = scan_repository(root)
        assert scan["finding_count"] == 1
        assert "private" not in json.dumps(scan)
        result = reconcile_scan(
            scan,
            {
                "schema_version": MANIFEST_SCHEMA,
                "required_discovery_sessions": [
                    {"id": "crm", "name": "CRM", "status": "required"}
                ],
                "touchpoints": [],
            },
        )
        assert not result["vault_boundary_ready"] and result["unknown_count"] == 1

        app, updates = root / "app", root / "updates"
        vault = root / "customer-data" / "Smoke.business-vault"
        layout = provision_business_vault(
            vault,
            business_name="Smoke Business",
            business_stable_id="smoke-business",
            application_root=app,
            update_root=updates,
        )
        assert layout.manifest.is_file() and layout.records.is_dir()
        try:
            provision_business_vault(
                app / "unsafe",
                business_name="Unsafe",
                business_stable_id="unsafe",
                application_root=app,
                update_root=updates,
            )
        except VaultBoundaryError:
            pass
        else:
            raise AssertionError("vault/application overlap was accepted")

        capability = classify_node(
            system="Windows",
            architecture="AMD64",
            os_release="11",
            cpu_logical_count=8,
            memory_bytes=16 * 1024**3,
            available_storage_bytes=100 * 1024**3,
        )
        release = {
            "schema_version": "tessaris.node-release-manifest.v1",
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
            "health_gates": ["guardian"],
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
                "runtime_trace_scenarios": ["foundation-smoke"],
                "runtime_trace_sha256": {
                    "business-onboarding": "1" * 64,
                    "boardroom-business-maps": "2" * 64,
                    "aion-pilot-conversations": "3" * 64,
                    "automations-schedules": "4" * 64,
                    "files-documents": "5" * 64,
                    "import-export-migration": "6" * 64,
                    "backup-recovery": "7" * 64,
                },
                "runtime_trace_surface_counts": {
                    "business-onboarding": 1,
                    "boardroom-business-maps": 1,
                    "aion-pilot-conversations": 1,
                    "automations-schedules": 1,
                    "files-documents": 1,
                    "import-export-migration": 1,
                    "backup-recovery": 1,
                },
                "runtime_trace_domain_counts": {
                    "business-onboarding": 8,
                    "boardroom-business-maps": 5,
                    "aion-pilot-conversations": 3,
                    "automations-schedules": 4,
                    "files-documents": 6,
                    "import-export-migration": 8,
                    "backup-recovery": 8,
                },
                "runtime_trace_external_class_counts": {
                    "business-onboarding": 1,
                    "boardroom-business-maps": 0,
                    "aion-pilot-conversations": 0,
                    "automations-schedules": 0,
                    "files-documents": 0,
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
                "learning.customer_state",
                "learning.audit",
                "train_agent.automations",
                "train_agent.runs_and_audit",
                "file_cabinet.tree",
                "file_cabinet.originals",
                "file_cabinet.governance",
                "vault.migration_receipts",
            ],
            "introduced_department_ids": [],
            "feature_data_changes": [],
            "release_change_inventory": {
                "schema_version": "tessaris.release-change-inventory.v1",
                "sha256": "b195c8c60fb386cc176353066396672d873fec88a6c596873634bfbea4308200",
                "feature_ids": [],
                "department_ids": [],
            },
        }
        preflight = evaluate_release_preflight(
            release,
            capability,
            current_version="1.1.0",
            guardian_api_version="guardian.v1",
            vault_schema_version="tessaris.business-vault.v1",
            signature_verified=True,
            repository_metadata_fresh=True,
        )
        assert preflight.eligible

        book = PhotonPriceBook(
            version="v1",
            currency="GBP",
            minor_units_per_1000_photons=1000,
            action_rates={"quote.prepared": 25},
            effective_at="future",
            region="GB",
            cohort="pilot",
            reason="pilot_calibration",
        )
        assert book.minor_units_for(25) == 25
        envelope = sign_price_book(book, _SmokeSigner())
        assert verify_price_book(envelope, verifier=_smoke_verify)
        ledger = PhotonLedger()
        ledger.post(
            transaction_id="grant-1",
            tenant_id="tenant-1",
            reason="allowance_grant",
            source_receipt_id="grant-receipt-1",
            rate_card_version="v1",
            idempotency_key="grant-1",
            recorded_at="t0",
            entries=[
                PhotonLedgerEntry("platform.allowance", -1000),
                PhotonLedgerEntry("customer.available", 1000),
            ],
        )
        wallet = PhotonWalletEngine(ledger, tenant_id="tenant-1", price_book=book)
        wallet.reserve(reservation_id="r1", action_type="quote.prepared", created_at="t1")
        wallet.release(reservation_id="r1", reason_code="outcome_failed", released_at="t2")
        assert wallet.available() == 1000
        wallet.reserve(reservation_id="r2", action_type="quote.prepared", created_at="t3")
        wallet.capture(
            reservation_id="r2",
            outcome_id="o2",
            device_id="device-1",
            tenant_commitment="tenant-hash",
            success_evidence_code="saved_verified",
            completed_at="t4",
        )
        assert wallet.available() == 975
        assert sum(ledger.balances(tenant_id="tenant-1").values()) == 0


if __name__ == "__main__":
    run()
    print("Vault, Node/update and Photon foundation smoke checks passed")
