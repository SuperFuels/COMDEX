"""Portable Legal signing evidence anchored to GlyphChain.

Documents and signer identities stay inside the originating Tessaris workspace.
The portable receipt contains a device-signed commitment and, when GlyphChain is
available, the finalized transaction and Merkle inclusion proof.
"""

from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.modules.chain_sim.document_proof import (
    DOCUMENT_PROOF_SCHEMA,
    DOCUMENT_PROOF_VERIFICATION_VERSION,
    normalize_document_proof_payload,
)
from backend.modules.aion_business.runtime.legal_secure_storage import LegalKeyStore
from backend.modules.aion_business.runtime.legal_resource_limits import (
    bounded_record_paths,
    ensure_workspace_record_write,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _signature_commitments(signers: list[Mapping[str, Any]]) -> list[str]:
    commitments: list[str] = []
    for signer in signers:
        signer_id = str(signer.get("signer_id") or "")
        identity_commitment = _digest({
            "signer_id": signer_id,
            "name": " ".join(str(signer.get("name") or "").split()).lower(),
            "email": str(signer.get("email") or "").strip().lower(),
        })
        commitments.append(_digest({
            "signer_id": signer_id,
            "signer_identity_commitment": identity_commitment,
            "signed_at": signer.get("signed_at"),
            "signature_method": signer.get("signature_method") or signer.get("method"),
            "accepted_document_hash": signer.get("accepted_document_hash"),
        }))
    return commitments


class LegalDocumentProofError(ValueError):
    pass


def _completed_at_ms(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        raise LegalDocumentProofError("completed_at_required")
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


class LegalDocumentProofService:
    """Create, submit and verify privacy-preserving signing evidence."""

    RECEIPT_VERSION = "tessaris.glyphchain-document-receipt.v2"
    POLICY_VERSION = "tessaris-controlled-electronic-signing.v1"
    PROTOCOL_VERSION = "glyphchain-document-proof-v1"
    TRANSACTION_HASH_VERSION = "glyphchain-ledger-envelope-sha256-v1"
    MAX_BUNDLE_BYTES = 16 * 1024 * 1024
    MAX_OUTBOX_ITEM_BYTES = 256 * 1024
    MAX_OUTBOX_ITEMS = 10_000
    MAX_JOURNAL_SEGMENT_BYTES = 16 * 1024 * 1024
    MAX_JOURNAL_SEGMENTS = 64
    MAX_MERKLE_PROOF_ITEMS = 256

    def __init__(
        self,
        root: str | Path,
        *,
        clock: Callable[[], datetime] = _utc_now,
        chain_submitter: Callable[[Mapping[str, Any], Ed25519PrivateKey], Mapping[str, Any]] | None = None,
        chain_submission_enabled: bool | None = None,
        key_store: LegalKeyStore | None = None,
    ) -> None:
        base = Path(root)
        self.root = base / "_portable_proofs"
        self.outbox_root = base / "_proof_outbox"
        self.identity_dir = base / "_device_identity"
        self.key_store = key_store or LegalKeyStore(base)
        self.clock = clock
        self._outbox_lock = threading.RLock()
        self.chain_submitter = chain_submitter or self._submit_to_glyphchain
        if chain_submission_enabled is None:
            chain_submission_enabled = os.getenv("GLYPHCHAIN_DOCUMENT_PROOF_ENABLE", "0").strip().lower() in {
                "1", "true", "yes", "on"
            }
        self.chain_submission_enabled = bool(chain_submission_enabled)

    def create_for_envelope(self, record: Mapping[str, Any]) -> dict[str, Any]:
        signed_copy = record.get("signed_copy") or {}
        document = record.get("document") or {}
        audit = list(record.get("audit_events") or [])
        if record.get("status") != "COMPLETED" or not signed_copy.get("manifest_hash"):
            raise LegalDocumentProofError("completed_signed_copy_required")
        if not document.get("content_hash") or not audit:
            raise LegalDocumentProofError("document_and_audit_commitments_required")

        signature_commitments = _signature_commitments(list(record.get("signers") or []))
        signing_key_version = self.key_store.active_signing_version()
        proof_seed = {
            "workspace_id": record.get("workspace_id"),
            "envelope_id": record.get("envelope_id"),
            "document_hash": document.get("content_hash"),
            "signed_copy_hash": signed_copy.get("manifest_hash"),
        }
        payload = normalize_document_proof_payload({
            "schema_version": DOCUMENT_PROOF_SCHEMA,
            "proof_id": f"proof-{_digest(proof_seed)[:40]}",
            "document_id_commitment": _digest({
                "workspace_id": record.get("workspace_id"),
                "envelope_id": record.get("envelope_id"),
                "document_id": document.get("document_id"),
            }),
            "document_hash": document.get("content_hash"),
            "signed_copy_hash": signed_copy.get("manifest_hash"),
            "signatures_root": _digest(signature_commitments),
            "audit_root": audit[-1].get("event_hash"),
            "issuer_key_id": self._device_key_id(signing_key_version),
            "completed_at_ms": _completed_at_ms(signed_copy.get("completed_at")),
            "policy_version": self.POLICY_VERSION,
            "verification_version": DOCUMENT_PROOF_VERIFICATION_VERSION,
        })

        private_key = self._private_key(signing_key_version)
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        chain_context = self._chain_context()
        attestation = {
            "receipt_version": self.RECEIPT_VERSION,
            "created_at": _iso(self.clock()),
            "glyphchain_payload": payload,
            "chain_context": chain_context,
            "origin_device": {
                "algorithm": "ed25519",
                "key_id": self._device_key_id(signing_key_version),
                "key_version": signing_key_version,
                "public_key_base64": base64.b64encode(public_bytes).decode("ascii"),
            },
        }
        bundle: dict[str, Any] = {
            **attestation,
            "device_signature_base64": base64.b64encode(private_key.sign(_canonical(attestation))).decode("ascii"),
            "privacy": {
                "document_content_on_glyphchain": False,
                "signer_identity_on_glyphchain": False,
                "glyphchain_values": "hash commitments only",
            },
            "glyphchain": {
                "status": "PENDING_GLYPHCHAIN_SUBMISSION",
                "network": "GlyphChain",
                "requires_photon": False,
                "moves_currency": False,
            },
        }
        self._write_bundle(record, bundle)
        self._enqueue(record, bundle)
        if self.chain_submission_enabled:
            bundle = self.submit_pending(record, bundle=bundle)
        return deepcopy(bundle)

    def submit_pending(
        self,
        record: Mapping[str, Any],
        *,
        bundle: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = dict(bundle or self.bundle_for_envelope(str(record["workspace_id"]), str(record["envelope_id"])))
        if str((current.get("glyphchain") or {}).get("status")) == "FINALIZED":
            self._mark_outbox(current, "FINALIZED", result=current.get("glyphchain"))
            return deepcopy(current)
        self._enqueue(record, current)
        try:
            chain_state = dict(current.get("glyphchain") or {})
            existing = None
            if (
                chain_state.get("status") == "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"
                and chain_state.get("tx_id")
                and chain_state.get("block_height")
            ):
                existing = {**chain_state, "applied": True}
            if existing is None:
                existing = self._existing_glyphchain_proof(current)
            if existing is not None:
                result = existing
            else:
                self._mark_outbox(current, "SUBMITTING")
                key_version = int((current.get("origin_device") or {}).get("key_version") or 1)
                result = dict(self.chain_submitter(current["glyphchain_payload"], self._private_key(key_version)))
            if result.get("applied") is not True or not result.get("tx_id") or not result.get("block_height"):
                raise LegalDocumentProofError(str(result.get("error") or "glyphchain_transaction_not_finalized"))
            if not result.get("quorum_finality_certificate"):
                try:
                    from backend.modules.consensus.engine import get_engine
                    finality = get_engine().finality_receipt(height=int(result["block_height"]))
                    if (
                        finality.get("found") is True
                        and str(finality.get("txs_root") or "") == str(result.get("txs_root") or "")
                        and finality.get("ledger_commitment")
                    ):
                        result.update({
                            "block_id": finality.get("block_id"),
                            "ledger_commitment": finality.get("ledger_commitment"),
                            "quorum_finality_certificate": finality.get("quorum_finality_certificate"),
                            "trusted_validator_set_root": finality.get("trusted_validator_set_root"),
                            "validator_set_checkpoint_id": finality.get("validator_set_checkpoint_id"),
                        })
                except Exception:
                    # Consensus may not be running in local/development mode;
                    # the durable outbox will check again on its next retry.
                    pass
            finality_certificate = deepcopy(result.get("quorum_finality_certificate"))
            anchored_finality = False
            if isinstance(finality_certificate, Mapping):
                try:
                    from backend.modules.consensus.finality_certificate import verify_finality_certificate
                    from backend.modules.consensus.finality_checkpoint import load_trusted_checkpoint_from_env
                    checkpoint = load_trusted_checkpoint_from_env()
                    verification = verify_finality_certificate(
                        finality_certificate,
                        trusted_validator_set_root=(checkpoint.validator_set_root if checkpoint else None),
                        expected_chain_id=str((current.get("chain_context") or {}).get("chain_id") or ""),
                        expected_height=int(result.get("block_height") or 0),
                        expected_block_id=(str(result.get("block_id")) if result.get("block_id") else None),
                        expected_ledger_commitment=(
                            str(result.get("ledger_commitment")) if result.get("ledger_commitment") else None
                        ),
                        expected_txs_root=str(result.get("txs_root") or ""),
                    )
                    anchored_finality = bool(
                        checkpoint
                        and verification.get("valid")
                        and verification.get("trust_anchor_verified") is True
                    )
                except Exception:
                    anchored_finality = False
            chain_status = "FINALIZED" if anchored_finality else "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"
            current["glyphchain"] = {
                "status": chain_status,
                **deepcopy(current.get("chain_context") or self._chain_context()),
                "transaction_type": "DOCUMENT_PROOF_V1",
                "tx_id": result.get("tx_id"),
                "tx_hash": result.get("tx_hash"),
                "block_height": result.get("block_height"),
                "block_id": result.get("block_id"),
                "tx_index": result.get("tx_index"),
                "txs_root": result.get("txs_root"),
                "ledger_commitment": result.get("ledger_commitment"),
                "proof": result.get("proof") or [],
                "transaction_envelope": deepcopy(result.get("transaction_envelope") or {}),
                "quorum_finality_certificate": finality_certificate,
                "trusted_validator_set_root": result.get("trusted_validator_set_root"),
                "ledger_committed_at": _iso(self.clock()),
                "finalized_at": (_iso(self.clock()) if anchored_finality else None),
                "requires_photon": False,
                "moves_currency": False,
            }
            self._mark_outbox(current, chain_status, result=current["glyphchain"])
        except Exception as exc:
            current["glyphchain"] = {
                "status": "SUBMISSION_FAILED_RETRY_AVAILABLE",
                "network": "GlyphChain",
                "error": str(exc)[:500],
                "updated_at": _iso(self.clock()),
                "requires_photon": False,
                "moves_currency": False,
            }
            self._mark_outbox(current, "RETRY_PENDING", error=str(exc))
        self._write_bundle(record, current)
        return deepcopy(current)

    def retry_due(
        self,
        *,
        limit: int = 25,
        force: bool = False,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Retry durable proof submissions after restart or temporary failure.

        The queue stores commitments and local identifiers only.  Every state
        transition is also appended to an fsync'd journal so recovery does not
        depend on an in-memory scheduler.
        """
        now = self.clock()
        attempted: list[dict[str, Any]] = []
        for path in self._outbox_item_paths():
            if len(attempted) >= max(1, min(int(limit), 250)):
                break
            item = json.loads(path.read_text(encoding="utf-8"))
            if item.get("status") == "FINALIZED":
                continue
            if workspace_id is not None and item.get("workspace_id") != workspace_id:
                continue
            due_at = self._parse_time(item.get("next_attempt_at"))
            if not force and due_at is not None and due_at > now:
                continue
            workspace_id = str(item.get("workspace_id") or "")
            envelope_id = str(item.get("envelope_id") or "")
            if not workspace_id or not envelope_id:
                continue
            try:
                bundle = self.bundle_for_envelope(workspace_id, envelope_id)
                result = self.submit_pending(
                    {"workspace_id": workspace_id, "envelope_id": envelope_id},
                    bundle=bundle,
                )
                attempted.append({
                    "proof_id": item.get("proof_id"),
                    "status": (result.get("glyphchain") or {}).get("status"),
                })
            except Exception as exc:
                self._mark_outbox_by_item(item, "RETRY_PENDING", error=str(exc))
                attempted.append({"proof_id": item.get("proof_id"), "status": "RETRY_PENDING"})
        status = self.outbox_status()
        if workspace_id is not None:
            status["items"] = [item for item in status["items"] if item.get("workspace_id") == workspace_id]
            counts: dict[str, int] = {}
            for item in status["items"]:
                value = str(item.get("status") or "UNKNOWN")
                counts[value] = counts.get(value, 0) + 1
            status["counts"] = counts
        return {"attempted": attempted, "attempted_count": len(attempted), **status}

    def outbox_status(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        items: list[dict[str, Any]] = []
        for path in self._outbox_item_paths():
            item = json.loads(path.read_text(encoding="utf-8"))
            status = str(item.get("status") or "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
            items.append({key: item.get(key) for key in (
                "proof_id", "workspace_id", "envelope_id", "status", "attempt_count",
                "next_attempt_at", "updated_at", "last_error",
            )})
        return {"counts": counts, "items": items}

    def bundle_for_envelope(self, workspace_id: str, envelope_id: str) -> dict[str, Any]:
        path = self._bundle_path(workspace_id, envelope_id)
        if not path.exists():
            raise LegalDocumentProofError("document_proof_not_found")
        if path.stat().st_size > self.MAX_BUNDLE_BYTES:
            raise LegalDocumentProofError("document_proof_bundle_too_large")
        return json.loads(path.read_text(encoding="utf-8"))

    def verify_bundle(
        self,
        bundle: Mapping[str, Any],
        document_content: str | None = None,
        private_signers: list[Mapping[str, Any]] | None = None,
        trusted_validator_set_root: str | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        try:
            if len(_canonical(bundle)) > self.MAX_BUNDLE_BYTES:
                return {
                    "valid": False,
                    "errors": ["document_proof_bundle_too_large"],
                    "device_attestation_valid": False,
                    "document_matches": None,
                    "private_signer_commitments_verified": None,
                    "glyphchain_status": "INVALID",
                    "glyphchain_inclusion_verified": None,
                    "glyphchain_transaction_payload_verified": None,
                    "glyphchain_quorum_finality_verified": None,
                    "glyphchain_quorum_finality_assurance": "INVALID",
                    "glyphchain_quorum_finality": None,
                    "chain_context": {},
                    "proof_id": None,
                }
        except (TypeError, ValueError):
            errors.append("document_proof_bundle_invalid")
        try:
            attestation = {
                "receipt_version": bundle["receipt_version"],
                "created_at": bundle["created_at"],
                "glyphchain_payload": bundle["glyphchain_payload"],
                "chain_context": bundle["chain_context"],
                "origin_device": bundle["origin_device"],
            }
            if attestation["receipt_version"] != self.RECEIPT_VERSION:
                errors.append("unsupported_receipt_version")
            normalize_document_proof_payload(attestation["glyphchain_payload"])
            public_key = Ed25519PublicKey.from_public_bytes(
                base64.b64decode(attestation["origin_device"]["public_key_base64"], validate=True)
            )
            public_key.verify(
                base64.b64decode(str(bundle["device_signature_base64"]), validate=True),
                _canonical(attestation),
            )
            if document_content is not None:
                supplied_hash = sha256(document_content.strip().encode("utf-8")).hexdigest()
                if supplied_hash != attestation["glyphchain_payload"]["document_hash"]:
                    errors.append("document_hash_mismatch")
        except (KeyError, TypeError, ValueError, InvalidSignature):
            errors.append("device_attestation_invalid")

        glyphchain = dict(bundle.get("glyphchain") or {})
        signer_commitments_verified: bool | None = None
        if private_signers is not None:
            signer_commitments_verified = hmac.compare_digest(
                _digest(_signature_commitments(private_signers)),
                str((bundle.get("glyphchain_payload") or {}).get("signatures_root") or ""),
            )
            if not signer_commitments_verified:
                errors.append("private_signer_commitments_mismatch")
        inclusion_verified: bool | None = None
        transaction_payload_verified: bool | None = None
        quorum_finality_verified: bool | None = None
        quorum_finality_result: dict[str, Any] | None = None
        quorum_finality_assurance = "NOT_AVAILABLE"
        if glyphchain.get("status") in {"FINALIZED", "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"} and glyphchain.get("tx_hash") and glyphchain.get("txs_root"):
            try:
                from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, verify_proof

                envelope = dict(glyphchain.get("transaction_envelope") or {})
                expected_envelope = {
                    "from_addr": envelope.get("from_addr"),
                    "nonce": int(envelope.get("nonce")),
                    "tx_type": envelope.get("tx_type"),
                    "payload": envelope.get("payload"),
                }
                transaction_payload_verified = bool(
                    expected_envelope["tx_type"] == "DOCUMENT_PROOF_V1"
                    and expected_envelope["payload"] == attestation["glyphchain_payload"]
                    and hmac.compare_digest(_digest(expected_envelope), str(glyphchain["tx_hash"]))
                    and str(glyphchain.get("tx_id") or "") == f"tx_{str(glyphchain['tx_hash'])[:12]}"
                )
                if not transaction_payload_verified:
                    errors.append("glyphchain_transaction_payload_mismatch")
                merkle_proof = glyphchain.get("proof") or []
                if not isinstance(merkle_proof, list) or len(merkle_proof) > self.MAX_MERKLE_PROOF_ITEMS:
                    raise ValueError("glyphchain_merkle_proof_limit_exceeded")
                inclusion_verified = verify_proof(
                    hash_leaf(bytes.fromhex(str(glyphchain["tx_hash"]))),
                    merkle_proof,
                    bytes.fromhex(str(glyphchain["txs_root"])),
                )
                if not inclusion_verified:
                    errors.append("glyphchain_inclusion_invalid")
                certificate = glyphchain.get("quorum_finality_certificate")
                if certificate:
                    from backend.modules.consensus.finality_certificate import verify_finality_certificate

                    effective_trusted_root = str(trusted_validator_set_root or "").strip() or None
                    trust_anchor_source = "caller" if effective_trusted_root else None
                    if effective_trusted_root is None:
                        try:
                            from backend.modules.consensus.finality_checkpoint import load_trusted_checkpoint_from_env
                            configured_checkpoint = load_trusted_checkpoint_from_env()
                            if configured_checkpoint is not None:
                                effective_trusted_root = configured_checkpoint.validator_set_root
                                trust_anchor_source = "operator_pinned_checkpoint"
                        except Exception:
                            # A missing or invalid local trust configuration
                            # must never be replaced by the root inside the receipt.
                            effective_trusted_root = None

                    quorum_finality_result = verify_finality_certificate(
                        certificate,
                        trusted_validator_set_root=effective_trusted_root,
                        expected_chain_id=str((bundle.get("chain_context") or {}).get("chain_id") or ""),
                        expected_height=int(glyphchain.get("block_height") or 0),
                        expected_block_id=(str(glyphchain.get("block_id")) if glyphchain.get("block_id") else None),
                        expected_ledger_commitment=(
                            str(glyphchain.get("ledger_commitment"))
                            if glyphchain.get("ledger_commitment") else None
                        ),
                        expected_txs_root=str(glyphchain.get("txs_root") or ""),
                    )
                    quorum_finality_result["trust_anchor_source"] = trust_anchor_source
                    if effective_trusted_root is None:
                        quorum_finality_verified = None
                        quorum_finality_assurance = (
                            "CERTIFICATE_INTEGRITY_ONLY"
                            if quorum_finality_result.get("certificate_integrity_verified") else "INVALID"
                        )
                        if not quorum_finality_result.get("certificate_integrity_verified"):
                            errors.append("glyphchain_quorum_finality_invalid")
                    else:
                        quorum_finality_verified = bool(
                            quorum_finality_result.get("valid")
                            and quorum_finality_result.get("trust_anchor_verified") is True
                        )
                        quorum_finality_assurance = "TRUST_ANCHORED" if quorum_finality_verified else "INVALID"
                    if effective_trusted_root is not None and not quorum_finality_verified:
                        errors.append("glyphchain_quorum_finality_invalid")
            except (KeyError, TypeError, ValueError):
                transaction_payload_verified = False
                if "glyphchain_transaction_payload_mismatch" not in errors:
                    errors.append("glyphchain_transaction_payload_mismatch")
                inclusion_verified = False
                errors.append("glyphchain_inclusion_invalid")

        return {
            "valid": not errors,
            "errors": errors,
            "device_attestation_valid": "device_attestation_invalid" not in errors,
            "document_matches": None if document_content is None else "document_hash_mismatch" not in errors,
            "private_signer_commitments_verified": signer_commitments_verified,
            "glyphchain_status": glyphchain.get("status", "NOT_SUBMITTED"),
            "glyphchain_inclusion_verified": inclusion_verified,
            "glyphchain_transaction_payload_verified": transaction_payload_verified,
            "glyphchain_quorum_finality_verified": quorum_finality_verified,
            "glyphchain_quorum_finality_assurance": quorum_finality_assurance,
            "glyphchain_quorum_finality": quorum_finality_result,
            "chain_context": deepcopy(bundle.get("chain_context") or {}),
            "proof_id": (bundle.get("glyphchain_payload") or {}).get("proof_id"),
        }

    def _chain_context(self) -> dict[str, str]:
        from backend.modules.chain_sim import chain_sim_config

        config = chain_sim_config.get_config() or {}
        return {
            "network": "GlyphChain",
            "chain_id": str(config.get("chain_id") or "glyphchain-dev"),
            "network_id": str(config.get("network_id") or "devnet"),
            "protocol_version": self.PROTOCOL_VERSION,
            "transaction_hash_version": self.TRANSACTION_HASH_VERSION,
        }

    def _submit_to_glyphchain(
        self,
        payload: Mapping[str, Any],
        private_key: Ed25519PrivateKey,
    ) -> Mapping[str, Any]:
        from backend.modules.chain_sim import chain_sim_config, chain_sim_model
        from backend.modules.chain_sim.chain_sim_ledger import get_tx
        from backend.modules.chain_sim.chain_sim_routes import DevSubmitTx, _submit_tx_sync_block, _tx_inclusion_proof

        public_bytes = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        from_addr = f"glyph1{sha256(public_bytes).hexdigest()[:38]}"
        nonce = int(chain_sim_model.get_or_create_account(from_addr).nonce or 0) + 1
        config = chain_sim_config.get_config() or {}
        chain_id = str(config.get("chain_id") or "glyphchain-dev")
        sign_dict = {
            "chain_id": chain_id,
            "from_addr": from_addr,
            "nonce": nonce,
            "tx_type": "DOCUMENT_PROOF_V1",
            "payload": dict(payload),
        }
        response = _submit_tx_sync_block(DevSubmitTx(
            **sign_dict,
            pubkey=public_bytes.hex(),
            signature=private_key.sign(_canonical(sign_dict)).hex(),
        ))
        result = json.loads(response.body)
        if result.get("applied") is True and result.get("tx_id"):
            stored = get_tx(str(result["tx_id"]))
            if stored:
                result.update(_tx_inclusion_proof(stored))
                result["transaction_envelope"] = {
                    "from_addr": stored.get("from_addr"),
                    "nonce": int(stored.get("nonce") or 0),
                    "tx_type": stored.get("tx_type"),
                    "payload": deepcopy(stored.get("payload") or {}),
                }
        return result

    def _existing_glyphchain_proof(self, bundle: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return an existing finalized proof before consuming another nonce."""
        from backend.modules.chain_sim.chain_sim_ledger import find_document_proof_tx
        from backend.modules.chain_sim.chain_sim_routes import _tx_inclusion_proof

        proof_id = str((bundle.get("glyphchain_payload") or {}).get("proof_id") or "")
        if not proof_id:
            return None
        existing = find_document_proof_tx(proof_id=proof_id)
        if not existing:
            return None
        result = dict(_tx_inclusion_proof(existing))
        result["applied"] = True
        result["transaction_envelope"] = {
            "from_addr": existing.get("from_addr"),
            "nonce": int(existing.get("nonce") or 0),
            "tx_type": existing.get("tx_type"),
            "payload": deepcopy(existing.get("payload") or {}),
        }
        return result

    def _enqueue(self, record: Mapping[str, Any], bundle: Mapping[str, Any]) -> None:
        payload = dict(bundle.get("glyphchain_payload") or {})
        proof_id = str(payload.get("proof_id") or "")
        if not proof_id:
            raise LegalDocumentProofError("proof_id_required_for_outbox")
        with self._outbox_lock:
            path = self._outbox_item_path(proof_id)
            if path.exists():
                return
            if len(self._outbox_item_paths()) >= self.MAX_OUTBOX_ITEMS:
                raise LegalDocumentProofError("proof_outbox_item_limit_exceeded")
            now = _iso(self.clock())
            item = {
                "schema_version": "tessaris.glyphchain-proof-outbox.v1",
                "proof_id": proof_id,
                "workspace_id": str(record["workspace_id"]),
                "envelope_id": str(record["envelope_id"]),
                "payload_hash": _digest(payload),
                "status": "PENDING",
                "attempt_count": 0,
                "created_at": now,
                "updated_at": now,
                "next_attempt_at": now,
                "last_error": None,
            }
            self._write_outbox_item(item)
            self._append_outbox_event(item, "ENQUEUED")

    def _mark_outbox(
        self,
        bundle: Mapping[str, Any],
        status: str,
        *,
        error: str | None = None,
        result: Mapping[str, Any] | None = None,
    ) -> None:
        proof_id = str((bundle.get("glyphchain_payload") or {}).get("proof_id") or "")
        if not proof_id:
            return
        path = self._outbox_item_path(proof_id)
        if not path.exists():
            return
        item = json.loads(path.read_text(encoding="utf-8"))
        self._mark_outbox_by_item(item, status, error=error, result=result)

    def _mark_outbox_by_item(
        self,
        item: Mapping[str, Any],
        status: str,
        *,
        error: str | None = None,
        result: Mapping[str, Any] | None = None,
    ) -> None:
        with self._outbox_lock:
            current = dict(item)
            now = self.clock()
            if status in {"SUBMITTING", "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"}:
                current["attempt_count"] = int(current.get("attempt_count") or 0) + 1
            current["status"] = status
            current["updated_at"] = _iso(now)
            current["last_error"] = str(error)[:500] if error else None
            if status in {"RETRY_PENDING", "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY"}:
                delay = min(3600, 2 ** min(int(current.get("attempt_count") or 1), 11))
                from datetime import timedelta
                current["next_attempt_at"] = _iso(now + timedelta(seconds=delay))
                if status == "LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY":
                    current["result"] = {
                        key: (result or {}).get(key)
                        for key in ("tx_id", "tx_hash", "block_height", "tx_index", "txs_root")
                    }
            elif status == "FINALIZED":
                current["next_attempt_at"] = None
                current["result"] = {
                    key: (result or {}).get(key)
                    for key in ("tx_id", "tx_hash", "block_height", "tx_index", "txs_root")
                }
            self._write_outbox_item(current)
            self._append_outbox_event(current, status)

    def _outbox_items_dir(self) -> Path:
        path = self.outbox_root / "items"
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        return path

    def _outbox_item_path(self, proof_id: str) -> Path:
        safe = "".join(char for char in proof_id if char.isalnum() or char in "-_")[:160]
        if not safe:
            raise LegalDocumentProofError("proof_id_required_for_outbox")
        return self._outbox_items_dir() / f"{safe}.json"

    def _write_outbox_item(self, item: Mapping[str, Any]) -> None:
        path = self._outbox_item_path(str(item["proof_id"]))
        temporary = path.with_suffix(".tmp")
        encoded = json.dumps(item, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
        if len(encoded) > self.MAX_OUTBOX_ITEM_BYTES:
            raise LegalDocumentProofError("proof_outbox_item_too_large")
        temporary.write_bytes(encoded)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def _append_outbox_event(self, item: Mapping[str, Any], event: str) -> None:
        self.outbox_root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.outbox_root, 0o700)
        entry = {
            "event": event,
            "proof_id": item.get("proof_id"),
            "status": item.get("status"),
            "attempt_count": item.get("attempt_count"),
            "occurred_at": item.get("updated_at"),
            "last_error": item.get("last_error"),
        }
        encoded = (json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        path = self._journal_path_for_append(len(encoded))
        with path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)

    def _outbox_item_paths(self) -> list[Path]:
        paths = bounded_record_paths(
            self._outbox_items_dir(), ("*.json",), error_type=LegalDocumentProofError,
        )
        if len(paths) > self.MAX_OUTBOX_ITEMS:
            raise LegalDocumentProofError("proof_outbox_item_limit_exceeded")
        return sorted(paths)

    def _journal_path_for_append(self, additional_bytes: int) -> Path:
        self.outbox_root.mkdir(parents=True, exist_ok=True)
        for index in range(1, self.MAX_JOURNAL_SEGMENTS + 1):
            path = (
                self.outbox_root / "events.jsonl"
                if index == 1 else self.outbox_root / f"events-{index:06d}.jsonl"
            )
            current = path.stat().st_size if path.exists() else 0
            if current + additional_bytes <= self.MAX_JOURNAL_SEGMENT_BYTES:
                return path
        raise LegalDocumentProofError("proof_outbox_journal_limit_exceeded")

    @staticmethod
    def _parse_time(value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        return datetime.fromisoformat(text.replace("Z", "+00:00"))

    def _private_key(self, version: int | None = None) -> Ed25519PrivateKey:
        path = self.identity_dir / "legal-proof-ed25519.pem"
        if path.exists():
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise LegalDocumentProofError("legal_proof_device_key_invalid")
            raw = key.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
            self.key_store.import_signing_key_bytes(raw, version=1)
            if self.key_store.signing_key_bytes(1) != raw:
                raise LegalDocumentProofError("legal_proof_device_key_migration_failed")
            path.unlink()
            return key
        try:
            return Ed25519PrivateKey.from_private_bytes(self.key_store.signing_key_bytes(version))
        except (RuntimeError, ValueError) as exc:
            raise LegalDocumentProofError("legal_proof_device_key_unavailable") from exc

    def _device_key_id(self, version: int | None = None) -> str:
        public_bytes = self._private_key(version).public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return f"ed25519:sha256:{sha256(public_bytes).hexdigest()}"

    def _proof_dir(self, record: Mapping[str, Any]) -> Path:
        safe_workspace = "".join(char for char in str(record["workspace_id"]) if char.isalnum() or char in "-_")[:120]
        path = self.root / safe_workspace
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _bundle_path(self, workspace_id: str, envelope_id: str) -> Path:
        return self._proof_dir({"workspace_id": workspace_id}) / f"{self._safe_envelope(envelope_id)}.tessaris-proof"

    def _write_bundle(self, record: Mapping[str, Any], bundle: Mapping[str, Any]) -> None:
        path = self._bundle_path(str(record["workspace_id"]), str(record["envelope_id"]))
        encoded = json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
        if len(encoded) > self.MAX_BUNDLE_BYTES:
            raise LegalDocumentProofError("document_proof_bundle_too_large")
        ensure_workspace_record_write(
            workspace_folder=path.parent,
            record_path=path,
            record_patterns=("*.tessaris-proof",),
            estimated_bytes=len(encoded),
            error_type=LegalDocumentProofError,
        )
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(encoded)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    @staticmethod
    def _safe_envelope(envelope_id: str) -> str:
        value = "".join(char for char in str(envelope_id) if char.isalnum() or char in "-_")[:120]
        if not value:
            raise LegalDocumentProofError("envelope_id_required")
        return value
