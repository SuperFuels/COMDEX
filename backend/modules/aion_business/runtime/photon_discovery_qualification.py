"""Fail-closed Photon qualification runtime for the Business Vault campaign.

This adapter composes the production Photon ledger, signed wallet, work receipt
outbox and Revolut fulfilment services without enabling any provider network
call.  It exists only in explicit discovery mode.  Hosted authority and bearer
material remain in the discovery secret store; the Business Vault receives
only content-free business receipts and audit projections.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import csv
from hashlib import sha256
import io
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonPriceBook,
    PhotonWalletEngine,
)
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneService,
    issue_control_plane_token,
)
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import PhotonRevolutFulfilment
from backend.modules.aion_business.runtime.photon_wallet_snapshot import PhotonWalletSnapshotAuthority
from backend.modules.aion_business.runtime.photon_work_receipt_outbox import PhotonWorkReceiptOutbox
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


@dataclass(frozen=True)
class PhotonDiscoveryQualificationContext:
    root: Path
    export_root: Path
    access_private_key: Ed25519PrivateKey
    wallet_private_key: Ed25519PrivateKey
    device_private_key: Ed25519PrivateKey
    ledger: PhotonLedgerStore
    revolut: PhotonRevolutFulfilment
    service: PhotonControlPlaneService
    wallet_public_key_path: Path


def _private_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        if path.is_symlink() or (path.stat().st_mode & 0o077):
            raise PermissionError("photon_qualification_private_key_permissions_invalid")
        value = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(value, Ed25519PrivateKey):
            raise ValueError("photon_qualification_private_key_invalid")
        return value
    value = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(value.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    os.chmod(path, 0o600)
    return value


def build_photon_discovery_qualification_context(
    *, secret_store_root: str | Path, export_root: str | Path,
) -> PhotonDiscoveryQualificationContext:
    root = Path(secret_store_root).expanduser().resolve() / "photon-qualification"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    exports = Path(export_root).expanduser().resolve()
    exports.mkdir(parents=True, exist_ok=True, mode=0o700)
    access = _private_key(root / "keys" / "access-authority.pem")
    wallet = _private_key(root / "keys" / "wallet-authority.pem")
    device = _private_key(root / "keys" / "device-authority.pem")
    wallet_public = root / "keys" / "wallet-authority-public.pem"
    if not wallet_public.exists():
        wallet_public.write_bytes(wallet.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        os.chmod(wallet_public, 0o600)
    state = root / "control-plane"
    ledger = PhotonLedgerStore(state / "ledger.sqlite3")
    revolut = PhotonRevolutFulfilment(state / "revolut-fulfilment.sqlite3", ledger=ledger)
    snapshots = PhotonWalletSnapshotAuthority(
        state / "wallet-snapshots.sqlite3", ledger=ledger,
        authority_private_key=wallet,
    )
    service = PhotonControlPlaneService(
        state / "access-audit.sqlite3", ledger=ledger,
        wallet_snapshots=snapshots, revolut=revolut,
    )
    return PhotonDiscoveryQualificationContext(
        root=root, export_root=exports, access_private_key=access,
        wallet_private_key=wallet, device_private_key=device, ledger=ledger,
        revolut=revolut, service=service, wallet_public_key_path=wallet_public,
    )


class _Verifier:
    def verify(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        return raw_body != b"" and headers.get("X-Qualification-Signature") == "verified"


class _Orders:
    def retrieve_order(self, order_id: str) -> dict[str, Any]:
        return {
            "id": order_id, "external_reference": "journey24-order-reference",
            "amount_minor": 1000, "currency": "GBP", "state": "completed",
            "capture_mode": "automatic", "updated_at": "2026-10-18T01:01:00+00:00",
        }


class _Refunds:
    def retrieve_refund(self, refund_id: str) -> dict[str, Any]:
        return {
            "id": refund_id, "order_id": "journey24-order", "amount_minor": 100,
            "currency": "GBP", "state": "completed",
            "updated_at": "2026-10-18T01:04:00+00:00",
        }


def _put_projection(
    store: VaultDomainStore, domain: str, business_id: str, entity_id: str,
    payload: dict[str, Any],
) -> None:
    current = store.get_optional(domain, workspace_id=business_id, entity_id=entity_id)
    if current is not None:
        if current["payload"] != payload:
            raise ValueError("photon_qualification_projection_conflict")
        return
    store.put(
        domain, workspace_id=business_id, entity_id=entity_id, payload=payload,
        expected_version=None,
        idempotency_key="photon-qualification-" + sha256(
            f"{domain}\0{entity_id}".encode("utf-8")
        ).hexdigest(),
        actor_id="photon-qualification-runtime",
    )


def execute_photon_discovery_qualification(
    context: PhotonDiscoveryQualificationContext, *, business_id: str,
    endpoint: str,
) -> dict[str, Any]:
    business_id = canonical_business_id(business_id)
    tenant_id = business_id
    intent = context.revolut.record_checkout_intent(
        order_id="journey24-order", external_reference="journey24-order-reference",
        tenant_id=tenant_id, product_id="journey24-bundle", photons=1000,
        amount_minor=1000, currency="GBP", price_book_version="journey24-v1",
        created_at="2026-10-18T01:00:00+00:00",
    )
    raw_order = b'{"event":"ORDER_COMPLETED","order_id":"journey24-order"}'
    grant = context.revolut.handle_webhook(
        raw_order, {"X-Qualification-Signature": "verified"},
        verifier=_Verifier(), orders=_Orders(),
    )
    grant_replay = context.revolut.handle_webhook(
        raw_order, {"X-Qualification-Signature": "verified"},
        verifier=_Verifier(), orders=_Orders(),
    )
    outbox = PhotonWorkReceiptOutbox(
        context.root / "node" / "work-receipts.sqlite3",
        tenant_commitment="journey24-tenant-commitment", device_id="journey24-node",
        device_private_key=context.device_private_key,
    )
    wallet = PhotonWalletEngine(
        context.ledger, tenant_id=tenant_id,
        price_book=PhotonPriceBook(
            version="journey24-v1", currency="GBP", minor_units_per_1000_photons=10,
            action_rates={"qualification.verified_outcome": 25},
            effective_at="2026-10-18T00:00:00+00:00", region="GB",
            cohort="qualification", reason="journey24 qualification only",
        ),
        receipt_sink=outbox,
    )
    wallet.reserve(
        reservation_id="journey24-reservation", action_type="qualification.verified_outcome",
        created_at="2026-10-18T01:02:00+00:00",
    )
    captured = wallet.capture(
        reservation_id="journey24-reservation", outcome_id="journey24-outcome",
        device_id="journey24-node", tenant_commitment="journey24-tenant-commitment",
        success_evidence_code="qualification.persisted",
        completed_at="2026-10-18T01:03:00+00:00",
    )
    raw_refund = b'{"event":"REFUND_COMPLETED","order_id":"journey24-order","refund_id":"journey24-refund"}'
    reversal = context.revolut.handle_refund_webhook(
        raw_refund, {"X-Qualification-Signature": "verified"},
        verifier=_Verifier(), refunds=_Refunds(),
    )
    reversal_replay = context.revolut.handle_refund_webhook(
        raw_refund, {"X-Qualification-Signature": "verified"},
        verifier=_Verifier(), refunds=_Refunds(),
    )
    records = context.revolut.billing_records(tenant_id=tenant_id)
    fields = sorted(records[0])
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    export_path = context.export_root / "journey24-photon-billing-receipts.csv"
    export_path.write_text(stream.getvalue(), encoding="utf-8")
    os.chmod(export_path, 0o600)

    domains = VaultDomainStore(
        configured_business_vault_runtime().guardian,
        actor_id="photon-qualification-runtime",
    )
    billing_record = records[0]
    work_receipt = captured["receipt"]
    _put_projection(domains, "finance.sales_records", business_id, "photon/journey24-billing", {
        "schema_version": "tessaris.photon-business-billing-projection.v1",
        "receipt_id": billing_record["receipt_id"],
        "record_hash": billing_record["record_hash"],
        "currency": billing_record["currency"],
        "amount_minor": billing_record["amount_minor"],
        "refunded_minor": billing_record["refunded_minor"],
        "photons_granted": billing_record["photons_granted"],
        "photons_reversed": billing_record["photons_reversed"],
        "customer_content_included": False,
        "local_model_tokens_billed": False,
    })
    _put_projection(domains, "train_agent.runs_and_audit", business_id, "photon/journey24-outcome", {
        "schema_version": "tessaris.photon-work-projection.v1",
        "receipt_id": work_receipt["receipt_id"],
        "receipt_hash": work_receipt["receipt_hash"],
        "outcome_id": work_receipt["outcome_id"],
        "action_type": work_receipt["action_type"],
        "photons": work_receipt["photons"],
        "success_evidence_code": work_receipt["success_evidence_code"],
        "customer_content_included": False,
        "local_model_tokens_billed": False,
    })
    _put_projection(domains, "security.audit", business_id, "photon/journey24-boundary", {
        "schema_version": "tessaris.photon-boundary-audit.v1",
        "event_type": "photon_qualification_completed",
        "billing_authority_location": "hosted_control_plane",
        "desktop_bearer_exposed_to_renderer": False,
        "customer_content_included": False,
        "local_model_tokens_billed": False,
        "ledger_healthy": context.ledger.integrity()["healthy"],
    })
    issued = datetime.now(UTC).replace(microsecond=0)
    token = issue_control_plane_token(
        token_id="journey24-desktop-token", subject_id="journey24-desktop",
        tenant_id=tenant_id, scopes=["wallet.read", "billing.read"],
        issued_at=issued.isoformat(), expires_at=(issued + timedelta(minutes=55)).isoformat(),
        authority_private_key=context.access_private_key,
    )
    session = {
        "schema_version": "tessaris.photon-desktop-session.v1",
        "endpoint": endpoint.rstrip("/"), "tenant_id": tenant_id,
        "access_token": token,
    }
    return {
        "session": session, "wallet_public_key_path": str(context.wallet_public_key_path),
        "intent": intent, "grant": grant, "grant_replay": grant_replay,
        "capture": {"state": captured["state"], "receipt_hash": work_receipt["receipt_hash"]},
        "reversal": reversal, "reversal_replay": reversal_replay,
        "billing_record": billing_record, "export_path": str(export_path),
        "ledger_integrity": context.ledger.integrity(),
        "customer_content_included": False, "local_model_tokens_billed": False,
    }
