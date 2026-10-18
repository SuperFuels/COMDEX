from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.modules.aion_business.runtime.business_vault import BusinessVaultLayout
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian, VaultGuardianError


OBJECT_SCHEMA = "tessaris.vault-object.v1"
MAX_OBJECT_BYTES = 64 * 1024 * 1024


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class VaultObjectError(ValueError):
    pass


class VaultObjectStore:
    """Encrypted original-file storage controlled by the semantic Guardian boundary."""

    def __init__(
        self,
        layout: BusinessVaultLayout,
        *,
        guardian: VaultGuardian,
        business_stable_id: str,
        encryption_key: bytes,
    ) -> None:
        if len(encryption_key) != 32:
            raise VaultObjectError("object_encryption_key_invalid")
        if guardian.layout.root != layout.root:
            raise VaultObjectError("object_guardian_vault_mismatch")
        if guardian.business_stable_id != business_stable_id:
            raise VaultObjectError("object_business_identity_mismatch")
        self.layout = layout
        self.guardian = guardian
        self.business_stable_id = business_stable_id
        self.cipher = AESGCM(bytes(encryption_key))
        self.objects = layout.files / "objects"
        self.objects.mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def _display_name(value: str) -> str:
        result = str(value or "").strip()
        if not result or len(result) > 255 or "\x00" in result or "/" in result or "\\" in result:
            raise VaultObjectError("object_original_name_invalid")
        return result

    @staticmethod
    def _content_type(value: str) -> str:
        result = str(value or "application/octet-stream").strip().lower()
        if not result or len(result) > 127 or any(char in result for char in "\r\n\x00"):
            raise VaultObjectError("object_content_type_invalid")
        return result

    def _aad(
        self,
        *,
        object_id: str,
        plaintext_sha256: str,
        byte_length: int,
        content_type: str,
    ) -> bytes:
        return _canonical(
            {
                "schema_version": OBJECT_SCHEMA,
                "business_stable_id": self.business_stable_id,
                "object_id": object_id,
                "plaintext_sha256": plaintext_sha256,
                "byte_length": byte_length,
                "content_type": content_type,
            }
        )

    def put_bytes(
        self,
        *,
        object_id: str,
        data: bytes,
        original_name: str,
        content_type: str,
        idempotency_key: str,
        actor_id: str,
        recorded_at: str,
    ) -> dict[str, object]:
        object_id = self.guardian._component(object_id, "object_id")
        idempotency_key = self.guardian._component(idempotency_key, "idempotency_key")
        actor_id = self.guardian._component(actor_id, "actor_id")
        original_name = self._display_name(original_name)
        content_type = self._content_type(content_type)
        raw = bytes(data)
        if not raw or len(raw) > MAX_OBJECT_BYTES:
            raise VaultObjectError("object_size_invalid")
        plaintext_hash = _sha256(raw)

        try:
            existing = self.guardian.get_record(collection="original_files", record_id=object_id)
        except KeyError:
            existing = None
        if existing:
            payload = existing["payload"]
            if payload.get("idempotency_key") == idempotency_key and payload.get("plaintext_sha256") == plaintext_hash:
                return self._public_metadata(existing, idempotent_replay=True)
            raise VaultObjectError("object_already_exists")

        nonce = os.urandom(12)
        aad = self._aad(
            object_id=object_id,
            plaintext_sha256=plaintext_hash,
            byte_length=len(raw),
            content_type=content_type,
        )
        ciphertext = self.cipher.encrypt(nonce, raw, aad)
        sealed = nonce + ciphertext
        sealed_hash = _sha256(sealed)
        relative_path = Path(sealed_hash[:2]) / f"{sealed_hash}.tvobj"
        destination = self.objects / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".guardian-object-", dir=destination.parent)
        temporary = Path(temporary_name)
        created = False
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(sealed)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            if destination.exists():
                if _sha256(destination.read_bytes()) != sealed_hash:
                    raise VaultObjectError("object_blob_collision")
                temporary.unlink(missing_ok=True)
            else:
                os.replace(temporary, destination)
                created = True
            response = self.guardian.put_record(
                collection="original_files",
                record_id=object_id,
                payload={
                    "schema_version": OBJECT_SCHEMA,
                    "object_id": object_id,
                    "original_name": original_name,
                    "content_type": content_type,
                    "byte_length": len(raw),
                    "plaintext_sha256": plaintext_hash,
                    "sealed_sha256": sealed_hash,
                    "blob_relpath": relative_path.as_posix(),
                    "idempotency_key": idempotency_key,
                },
                expected_version=None,
                idempotency_key=f"file-{idempotency_key}",
                actor_id=actor_id,
                recorded_at=recorded_at,
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            if created:
                destination.unlink(missing_ok=True)
            raise
        record = self.guardian.get_record(
            collection="original_files", record_id=object_id, version=int(response["version"])
        )
        public = self._public_metadata(record, idempotent_replay=False)
        # The immutable write receipt is returned by put_record rather than by
        # get_record.  Preserve it in the caller-safe metadata so importing
        # services can retain proof that the encrypted original was committed.
        public["receipt_hash"] = response.get("receipt_hash")
        return public

    @staticmethod
    def _public_metadata(record: dict[str, object], *, idempotent_replay: bool) -> dict[str, object]:
        payload = dict(record["payload"])
        payload.pop("idempotency_key", None)
        payload.pop("blob_relpath", None)
        payload["version"] = record["version"]
        payload["receipt_hash"] = record.get("receipt_hash")
        payload["idempotent_replay"] = idempotent_replay
        return payload

    def get_bytes(self, *, object_id: str) -> tuple[dict[str, object], bytes]:
        object_id = self.guardian._component(object_id, "object_id")
        record = self.guardian.get_record(collection="original_files", record_id=object_id)
        payload = record["payload"]
        relative = Path(str(payload["blob_relpath"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("object_blob_path_invalid")
        blob = self.objects / relative
        sealed = blob.read_bytes()
        if _sha256(sealed) != payload["sealed_sha256"] or len(sealed) < 29:
            raise RuntimeError("object_sealed_integrity_failed")
        raw = self.cipher.decrypt(
            sealed[:12],
            sealed[12:],
            self._aad(
                object_id=object_id,
                plaintext_sha256=str(payload["plaintext_sha256"]),
                byte_length=int(payload["byte_length"]),
                content_type=str(payload["content_type"]),
            ),
        )
        if len(raw) != int(payload["byte_length"]) or _sha256(raw) != payload["plaintext_sha256"]:
            raise RuntimeError("object_plaintext_integrity_failed")
        return self._public_metadata(record, idempotent_replay=False), raw

    def tombstone(
        self,
        *,
        object_id: str,
        expected_version: int,
        reason_code: str,
        idempotency_key: str,
        actor_id: str,
        recorded_at: str,
    ) -> dict[str, object]:
        return self.guardian.tombstone_record(
            collection="original_files",
            record_id=object_id,
            expected_version=expected_version,
            reason_code=reason_code,
            idempotency_key=f"file-delete-{idempotency_key}",
            actor_id=actor_id,
            recorded_at=recorded_at,
        )
