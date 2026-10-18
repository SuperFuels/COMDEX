"""Authenticated Legal record storage with production Keychain custody."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import secrets
import threading
from typing import Any, Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from backend.modules.aion_business.runtime.legal_resource_limits import (
    configured_legal_record_bytes_limit,
)


SCHEMA_VERSION = "tessaris.legal-encrypted-record.v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _component(value: str, label: str) -> str:
    clean = str(value or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if not clean or clean in {".", ".."} or any(char not in allowed for char in clean):
        raise ValueError(f"invalid_{label}")
    return clean


class LegalKeyStore:
    """Resolve Legal keys without storing production key material beside records."""

    SERVICE = "ai.tessaris.legal"
    MAX_RETAINED_KEY_VERSIONS = 4_096
    MAX_METADATA_BYTES = 4 * 1024 * 1024

    def __init__(self, root: str | Path, *, runtime_mode: str | None = None) -> None:
        self.root = Path(root)
        self.runtime_mode = str(runtime_mode or os.getenv("TESSARIS_RUNTIME_MODE") or "development").lower()
        self.source = ""
        self._lock = threading.RLock()
        self.metadata_path = self.root / "_key_metadata.json"

    def active_encryption_version(self, workspace_id: str, purpose: str) -> int:
        workspace = _component(workspace_id, "workspace_id")
        purpose = _component(purpose, "key_purpose")
        return int(self._metadata()["active"].get(f"storage:{purpose}:{workspace}", 1))

    def encryption_key(self, workspace_id: str, purpose: str, version: int | None = None) -> bytes:
        workspace = _component(workspace_id, "workspace_id")
        purpose = _component(purpose, "key_purpose")
        version = int(version or self.active_encryption_version(workspace, purpose))
        account = f"storage:{purpose}:{workspace}:v{int(version)}"
        return self._key(account, remember=True)

    def active_signing_version(self) -> int:
        return int(self._metadata()["active"].get("proof-signing:device", 1))

    def signing_key_bytes(self, version: int | None = None) -> bytes:
        version = int(version or self.active_signing_version())
        return self._key(f"proof-signing:device:v{version}", remember=True)

    def rotate_encryption_key(self, workspace_id: str, purpose: str) -> dict[str, Any]:
        workspace = _component(workspace_id, "workspace_id")
        purpose = _component(purpose, "key_purpose")
        scope = f"storage:{purpose}:{workspace}"
        with self._lock:
            metadata = self._metadata()
            previous = int(metadata["active"].get(scope, 1))
            version = previous + 1
            self._key(f"{scope}:v{version}", remember=False)
            metadata["active"][scope] = version
            self._remember(metadata, f"{scope}:v{version}")
            self._write_metadata(metadata)
        return {"scope": scope, "previous_version": previous, "active_version": version}

    def rotate_signing_key(self) -> dict[str, Any]:
        scope = "proof-signing:device"
        with self._lock:
            metadata = self._metadata()
            previous = int(metadata["active"].get(scope, 1))
            version = previous + 1
            self._key(f"{scope}:v{version}", remember=False)
            metadata["active"][scope] = version
            self._remember(metadata, f"{scope}:v{version}")
            self._write_metadata(metadata)
        return {"scope": scope, "previous_version": previous, "active_version": version}

    def import_signing_key_bytes(self, value: bytes, version: int = 1) -> None:
        if len(value) != 32:
            raise ValueError("Legal signing key must be 32 bytes")
        account = f"proof-signing:device:v{int(version)}"
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring

                existing = str(keyring.get_password(self.SERVICE, account) or "").strip()
                if existing and base64.b64decode(existing, validate=True) != value:
                    raise RuntimeError("A different Legal signing key already exists in Keychain")
                keyring.set_password(self.SERVICE, account, base64.b64encode(value).decode("ascii"))
                self.source = "platform_keychain"
                self._remember_account(account)
                return
            except Exception as exc:
                raise RuntimeError("Legal production Keychain is unavailable") from exc
        folder = self.root / "_secure_keys"
        folder.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        path = folder / f"{account.replace(':', '-')}.key"
        if path.exists() and path.read_bytes() != value:
            raise RuntimeError("A different Legal signing key already exists")
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(value)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        self.source = "owner_only_development_file"
        self._remember_account(account)

    def status(self) -> dict[str, Any]:
        metadata = self._metadata()
        return {
            "key_source": "platform_keychain" if self.runtime_mode in {"production", "prod"} else "owner_only_development_file",
            "active": dict(metadata["active"]),
            "retained_key_versions": len(metadata["accounts"]),
            "raw_keys_exposed": False,
        }

    def export_recovery_bundle(self, password: str) -> dict[str, Any]:
        if len(str(password)) < 12:
            raise ValueError("legal_recovery_password_minimum_12_characters")
        metadata = self._metadata()
        payload = {
            "schema_version": "tessaris.legal-key-recovery.v1",
            "metadata": metadata,
            "keys": {
                account: base64.b64encode(self._key(account, remember=False)).decode("ascii")
                for account in metadata["accounts"]
            },
        }
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(str(password).encode("utf-8"))
        header = {
            "schema_version": "tessaris.legal-key-recovery-envelope.v1",
            "kdf": "scrypt-n16384-r8-p1",
            "cipher": "AES-256-GCM",
        }
        encrypted = AESGCM(key).encrypt(nonce, _canonical(payload), _canonical(header))
        return {
            "header": header,
            "salt_base64": base64.b64encode(salt).decode("ascii"),
            "nonce_base64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_base64": base64.b64encode(encrypted).decode("ascii"),
        }

    def import_recovery_bundle(self, package: Mapping[str, Any], password: str) -> dict[str, Any]:
        if len(str(password)) < 12:
            raise ValueError("legal_recovery_password_minimum_12_characters")
        header = dict(package.get("header") or {})
        expected = {
            "schema_version": "tessaris.legal-key-recovery-envelope.v1",
            "kdf": "scrypt-n16384-r8-p1",
            "cipher": "AES-256-GCM",
        }
        if header != expected:
            raise ValueError("legal_recovery_header_invalid")
        try:
            salt = base64.b64decode(str(package["salt_base64"]), validate=True)
            nonce = base64.b64decode(str(package["nonce_base64"]), validate=True)
            ciphertext = base64.b64decode(str(package["ciphertext_base64"]), validate=True)
            key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(str(password).encode("utf-8"))
            payload = json.loads(AESGCM(key).decrypt(nonce, ciphertext, _canonical(header)))
        except Exception:
            raise PermissionError("Legal recovery bundle could not be authenticated") from None
        if payload.get("schema_version") != "tessaris.legal-key-recovery.v1":
            raise ValueError("legal_recovery_payload_invalid")
        metadata = dict(payload.get("metadata") or {})
        if not isinstance(metadata.get("active"), dict) or not isinstance(metadata.get("accounts"), list):
            raise ValueError("legal_recovery_metadata_invalid")
        if len(metadata["accounts"]) > self.MAX_RETAINED_KEY_VERSIONS:
            raise ValueError("legal_recovery_key_version_limit_exceeded")
        raw_keys = payload.get("keys") or {}
        if not isinstance(raw_keys, dict) or len(raw_keys) > self.MAX_RETAINED_KEY_VERSIONS:
            raise ValueError("legal_recovery_key_version_limit_exceeded")
        decoded: dict[str, bytes] = {}
        for account, encoded in raw_keys.items():
            value = base64.b64decode(str(encoded), validate=True)
            if len(value) != 32:
                raise ValueError("legal_recovery_key_invalid")
            existing = self._existing_key(str(account))
            if existing is not None and existing != value:
                raise RuntimeError("Legal recovery would replace an existing key")
            decoded[str(account)] = value
        restored = 0
        for account, value in decoded.items():
            self._store_key(str(account), value, allow_existing_equal=True)
            restored += 1
        self._write_metadata(metadata)
        return {"restored_key_versions": restored, "raw_keys_exposed": False}

    def _key(self, account: str, *, remember: bool) -> bytes:
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring

                encoded = str(keyring.get_password(self.SERVICE, account) or "").strip()
                if not encoded:
                    encoded = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
                    keyring.set_password(self.SERVICE, account, encoded)
                key = base64.b64decode(encoded, validate=True)
            except Exception as exc:
                raise RuntimeError("Legal production Keychain is unavailable") from exc
            if len(key) != 32:
                raise RuntimeError("Legal Keychain item is invalid")
            self.source = "platform_keychain"
            if remember:
                self._remember_account(account)
            return key

        folder = self.root / "_secure_keys"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(folder, 0o700)
        except OSError:
            pass
        safe = account.replace(":", "-")
        path = folder / f"{safe}.key"
        if not path.exists():
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(secrets.token_bytes(32))
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        key = path.read_bytes()
        if len(key) != 32:
            raise RuntimeError("Legal development key file is invalid")
        self.source = "owner_only_development_file"
        if remember:
            self._remember_account(account)
        return key

    def _store_key(self, account: str, value: bytes, *, allow_existing_equal: bool) -> None:
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring

                existing = str(keyring.get_password(self.SERVICE, account) or "").strip()
                if existing and (not allow_existing_equal or base64.b64decode(existing, validate=True) != value):
                    raise RuntimeError("Legal recovery would replace an existing key")
                keyring.set_password(self.SERVICE, account, base64.b64encode(value).decode("ascii"))
                return
            except Exception as exc:
                raise RuntimeError("Legal production Keychain is unavailable") from exc
        folder = self.root / "_secure_keys"
        folder.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        path = folder / f"{account.replace(':', '-')}.key"
        if path.exists() and (not allow_existing_equal or path.read_bytes() != value):
            raise RuntimeError("Legal recovery would replace an existing key")
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(value)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def _existing_key(self, account: str) -> bytes | None:
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring

                encoded = str(keyring.get_password(self.SERVICE, account) or "").strip()
                return base64.b64decode(encoded, validate=True) if encoded else None
            except Exception as exc:
                raise RuntimeError("Legal production Keychain is unavailable") from exc
        path = self.root / "_secure_keys" / f"{account.replace(':', '-')}.key"
        return path.read_bytes() if path.exists() else None

    def _metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {"schema_version": "tessaris.legal-key-metadata.v1", "active": {}, "accounts": []}
        if self.metadata_path.stat().st_size > self.MAX_METADATA_BYTES:
            raise RuntimeError("Legal key metadata exceeds its size limit")
        value = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "tessaris.legal-key-metadata.v1":
            raise RuntimeError("Legal key metadata is unsupported")
        value.setdefault("active", {})
        value.setdefault("accounts", [])
        if len(value["accounts"]) > self.MAX_RETAINED_KEY_VERSIONS:
            raise RuntimeError("Legal key metadata exceeds its key-version limit")
        return value

    @staticmethod
    def _remember(metadata: dict[str, Any], account: str) -> None:
        accounts = metadata.setdefault("accounts", [])
        if account not in accounts:
            if len(accounts) >= LegalKeyStore.MAX_RETAINED_KEY_VERSIONS:
                raise RuntimeError("Legal key-version limit reached")
            accounts.append(account)
            accounts.sort()

    def _remember_account(self, account: str) -> None:
        with self._lock:
            metadata = self._metadata()
            before = list(metadata["accounts"])
            self._remember(metadata, account)
            if metadata["accounts"] != before:
                self._write_metadata(metadata)

    def _write_metadata(self, metadata: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        temporary = self.metadata_path.with_suffix(".tmp")
        temporary.write_bytes(_canonical(dict(metadata)))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.metadata_path)


class LegalEncryptedStore:
    def __init__(self, root: str | Path, *, purpose: str, key_store: LegalKeyStore | None = None) -> None:
        self.root = Path(root)
        self.purpose = _component(purpose, "storage_purpose")
        self.keys = key_store or LegalKeyStore(self.root)

    def write(self, path: Path, value: Mapping[str, Any], *, workspace_id: str, record_id: str) -> None:
        workspace = _component(workspace_id, "workspace_id")
        record = _component(record_id, "record_id")
        key_version = self.keys.active_encryption_version(workspace, self.purpose)
        header = {
            "schema_version": SCHEMA_VERSION,
            "purpose": self.purpose,
            "workspace_id": workspace,
            "record_id": record,
            "key_version": key_version,
            "cipher": "AES-256-GCM",
        }
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self.keys.encryption_key(workspace, self.purpose, key_version)).encrypt(
            nonce, _canonical(dict(value)), _canonical(header)
        )
        envelope = {
            **header,
            "nonce_base64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_base64": base64.b64encode(ciphertext).decode("ascii"),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        encoded_envelope = _canonical(envelope)
        if len(encoded_envelope) > configured_legal_record_bytes_limit():
            raise ValueError("legal_encrypted_record_size_limit_exceeded")
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(encoded_envelope)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def read(self, path: Path, *, workspace_id: str, record_id: str) -> dict[str, Any]:
        workspace = _component(workspace_id, "workspace_id")
        record = _component(record_id, "record_id")
        if path.stat().st_size > configured_legal_record_bytes_limit():
            raise PermissionError("Legal encrypted record exceeds its size limit")
        envelope = json.loads(path.read_text(encoding="utf-8"))
        header = {
            key: envelope.get(key)
            for key in ("schema_version", "purpose", "workspace_id", "record_id", "key_version", "cipher")
        }
        expected = {
            "schema_version": SCHEMA_VERSION,
            "purpose": self.purpose,
            "workspace_id": workspace,
            "record_id": record,
            "key_version": int(header.get("key_version") or 0),
            "cipher": "AES-256-GCM",
        }
        if header != expected or expected["key_version"] < 1:
            raise PermissionError("Legal encrypted-record context does not match")
        try:
            plaintext = AESGCM(self.keys.encryption_key(workspace, self.purpose, expected["key_version"])).decrypt(
                base64.b64decode(str(envelope["nonce_base64"]), validate=True),
                base64.b64decode(str(envelope["ciphertext_base64"]), validate=True),
                _canonical(header),
            )
            value = json.loads(plaintext)
        except Exception:
            raise PermissionError("Legal encrypted record could not be authenticated") from None
        if not isinstance(value, dict):
            raise PermissionError("Legal encrypted record payload is invalid")
        return value

    def migrate_plaintext(
        self,
        plaintext_path: Path,
        encrypted_path: Path,
        *,
        workspace_id: str,
        record_id: str,
    ) -> dict[str, Any]:
        if plaintext_path.stat().st_size > configured_legal_record_bytes_limit():
            raise PermissionError("Legal plaintext migration record exceeds its size limit")
        value = json.loads(plaintext_path.read_text(encoding="utf-8"))
        self.write(encrypted_path, value, workspace_id=workspace_id, record_id=record_id)
        verified = self.read(encrypted_path, workspace_id=workspace_id, record_id=record_id)
        if verified != value:
            raise RuntimeError("Legal plaintext migration verification failed")
        plaintext_path.unlink()
        return verified
