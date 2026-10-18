"""Self-sovereign application-account recovery authority.

This module deliberately separates account ownership from a device backup.  An
encrypted recovery kit must be retained outside the Tessaris runtime, while a
signed public account descriptor can be independently published or retained.
Recovery proves control of the stable account root, advances a monotonic epoch
and invalidates every device from the previous descriptor.

Freshness is not self-asserting: production recovery must obtain the current
descriptor (or its digest) from an independent account registry/release channel.
The local implementation verifies that descriptor but does not pretend to be
the independent registry.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


class ApplicationAccountRecoveryError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _component(value: str, label: str) -> str:
    clean = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", clean) or clean in {".", ".."}:
        raise ApplicationAccountRecoveryError(f"invalid_{label}")
    return clean


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


class ApplicationAccountRecoveryStore:
    """Own a stable account root and perform clean-device recovery."""

    DESCRIPTOR_SCHEMA = "tessaris.application-account-descriptor.v1"
    KIT_SCHEMA = "tessaris.application-account-recovery-kit.v1"
    KIT_ENVELOPE_SCHEMA = "tessaris.application-account-recovery-envelope.v1"
    SERVICE = "ai.tessaris.application-account-recovery"
    MAX_KIT_BYTES = 256 * 1024
    MAX_DEVICES = 64
    MIN_PASSWORD_CHARS = 16

    def __init__(self, root: str | Path, *, runtime_mode: str | None = None) -> None:
        self.root = Path(root).expanduser().resolve()
        self.runtime_mode = str(
            runtime_mode or os.getenv("TESSARIS_RUNTIME_MODE") or "development"
        ).strip().lower()
        self.state_path = self.root / "account-descriptor.json"
        self.development_key_path = self.root / "_secure_account_root.key"

    def initialize(
        self,
        *,
        workspace_id: str,
        owner_id: str,
        device_id: str,
        password: str,
        recovery_kit_path: str | Path,
        confirmation: str,
    ) -> dict[str, Any]:
        if confirmation != "CREATE OFF-DEVICE ACCOUNT RECOVERY KIT":
            raise ApplicationAccountRecoveryError("account_recovery_initialization_confirmation_required")
        self._validate_password(password)
        workspace = _component(workspace_id, "workspace_id")
        device = _component(device_id, "device_id")
        owner = str(owner_id or "").strip()
        if not owner:
            raise ApplicationAccountRecoveryError("account_owner_required")
        if self.state_path.exists():
            raise ApplicationAccountRecoveryError("application_account_already_initialized")
        kit_path = self._off_device_kit_path(recovery_kit_path)
        if kit_path.exists():
            raise ApplicationAccountRecoveryError("account_recovery_kit_destination_exists")

        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes_raw()
        public_bytes = private_key.public_key().public_bytes_raw()
        account_id = self._account_id(public_bytes)
        descriptor = self._signed_descriptor(
            private_key,
            account_id=account_id,
            workspace_id=workspace,
            epoch=1,
            active_devices=[device],
            previous_descriptor_sha256=None,
            event_type="ACCOUNT_INITIALIZED",
            event_actor_hash=sha256(owner.encode("utf-8")).hexdigest(),
        )
        kit = self._encrypt_kit(
            password=password,
            account_id=account_id,
            workspace_id=workspace,
            public_key=public_bytes,
            private_key=private_bytes,
        )
        self._store_root_key(account_id, private_bytes)
        self._write_descriptor(descriptor)
        self._write_kit(kit_path, kit)
        return {
            "account_id": account_id,
            "workspace_id": workspace,
            "recovery_epoch": 1,
            "descriptor": descriptor,
            "descriptor_sha256": _digest(descriptor),
            "recovery_kit_path": str(kit_path),
            "recovery_kit_shown_once": True,
            "off_device_retention_required": True,
            "raw_private_key_exposed": False,
        }

    def recover_clean_device(
        self,
        *,
        recovery_kit_path: str | Path,
        password: str,
        current_descriptor: Mapping[str, Any],
        expected_account_id: str,
        new_device_id: str,
        actor_id: str,
        confirmation: str,
    ) -> dict[str, Any]:
        if confirmation != "RECOVER ACCOUNT AND REVOKE PRIOR DEVICES":
            raise ApplicationAccountRecoveryError("account_recovery_confirmation_required")
        self._validate_password(password)
        if self.state_path.exists():
            raise ApplicationAccountRecoveryError("clean_account_recovery_target_required")
        device = _component(new_device_id, "device_id")
        actor = str(actor_id or "").strip()
        if not actor:
            raise ApplicationAccountRecoveryError("account_recovery_actor_required")
        descriptor = self.verify_descriptor(current_descriptor)
        expected = str(expected_account_id or "").strip()
        if not expected or not hmac.compare_digest(descriptor["account_id"], expected):
            raise PermissionError("account_recovery_expected_account_mismatch")

        kit = self._read_kit(recovery_kit_path)
        recovered = self._decrypt_kit(kit, password=password)
        if not hmac.compare_digest(recovered["account_id"], expected):
            raise PermissionError("account_recovery_kit_account_mismatch")
        if not hmac.compare_digest(recovered["workspace_id"], descriptor["workspace_id"]):
            raise PermissionError("account_recovery_workspace_mismatch")
        private_bytes = recovered["private_key"]
        private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
        public_bytes = private_key.public_key().public_bytes_raw()
        if not hmac.compare_digest(public_bytes, recovered["public_key"]):
            raise PermissionError("account_recovery_key_pair_mismatch")
        if not hmac.compare_digest(self._account_id(public_bytes), expected):
            raise PermissionError("account_recovery_root_identity_mismatch")

        next_descriptor = self._signed_descriptor(
            private_key,
            account_id=expected,
            workspace_id=descriptor["workspace_id"],
            epoch=int(descriptor["recovery_epoch"]) + 1,
            active_devices=[device],
            previous_descriptor_sha256=_digest(descriptor),
            event_type="ACCOUNT_RECOVERED_PRIOR_DEVICES_REVOKED",
            event_actor_hash=sha256(actor.encode("utf-8")).hexdigest(),
        )
        self._store_root_key(expected, private_bytes)
        self._write_descriptor(next_descriptor)
        return {
            "recovered": True,
            "account_id": expected,
            "workspace_id": descriptor["workspace_id"],
            "recovery_epoch": next_descriptor["recovery_epoch"],
            "prior_devices_revoked": list(descriptor["active_devices"]),
            "active_devices": [device],
            "descriptor": next_descriptor,
            "descriptor_sha256": _digest(next_descriptor),
            "previous_descriptor_sha256": _digest(descriptor),
            "independent_freshness_required": True,
            "raw_private_key_exposed": False,
        }

    def descriptor(self) -> dict[str, Any]:
        if not self.state_path.is_file() or self.state_path.is_symlink():
            raise ApplicationAccountRecoveryError("application_account_not_initialized")
        if self.state_path.stat().st_size > self.MAX_KIT_BYTES:
            raise ApplicationAccountRecoveryError("application_account_descriptor_too_large")
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ApplicationAccountRecoveryError("application_account_descriptor_unreadable") from exc
        return self.verify_descriptor(value)

    def authorize_device(self, *, device_id: str, recovery_epoch: int) -> dict[str, Any]:
        descriptor = self.descriptor()
        device = _component(device_id, "device_id")
        if int(recovery_epoch) != int(descriptor["recovery_epoch"]):
            raise PermissionError("application_account_session_epoch_revoked")
        if device not in descriptor["active_devices"]:
            raise PermissionError("application_account_device_revoked")
        return {
            "authorized": True,
            "account_id": descriptor["account_id"],
            "workspace_id": descriptor["workspace_id"],
            "recovery_epoch": descriptor["recovery_epoch"],
            "device_id": device,
        }

    @classmethod
    def verify_descriptor(
        cls,
        value: Mapping[str, Any],
        *,
        expected_account_id: str | None = None,
        expected_previous_descriptor_sha256: str | None = None,
    ) -> dict[str, Any]:
        descriptor = dict(value or {})
        if descriptor.get("schema_version") != cls.DESCRIPTOR_SCHEMA:
            raise ApplicationAccountRecoveryError("application_account_descriptor_schema_invalid")
        signature_encoded = str(descriptor.pop("signature_base64", ""))
        try:
            public_bytes = base64.b64decode(str(descriptor["root_public_key_base64"]), validate=True)
            signature = base64.b64decode(signature_encoded, validate=True)
        except Exception as exc:
            raise ApplicationAccountRecoveryError("application_account_descriptor_encoding_invalid") from exc
        if len(public_bytes) != 32 or len(signature) != 64:
            raise ApplicationAccountRecoveryError("application_account_descriptor_key_invalid")
        account_id = cls._account_id(public_bytes)
        if not hmac.compare_digest(str(descriptor.get("account_id") or ""), account_id):
            raise PermissionError("application_account_descriptor_identity_invalid")
        if expected_account_id and not hmac.compare_digest(account_id, str(expected_account_id)):
            raise PermissionError("application_account_descriptor_unexpected_account")
        try:
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, _canonical(descriptor))
        except Exception:
            raise PermissionError("application_account_descriptor_signature_invalid") from None
        workspace = _component(str(descriptor.get("workspace_id") or ""), "workspace_id")
        epoch = int(descriptor.get("recovery_epoch") or 0)
        if epoch < 1:
            raise ApplicationAccountRecoveryError("application_account_descriptor_epoch_invalid")
        devices = descriptor.get("active_devices")
        if not isinstance(devices, list) or not devices or len(devices) > cls.MAX_DEVICES:
            raise ApplicationAccountRecoveryError("application_account_descriptor_devices_invalid")
        clean_devices = [_component(str(item), "device_id") for item in devices]
        if len(set(clean_devices)) != len(clean_devices):
            raise ApplicationAccountRecoveryError("application_account_descriptor_devices_invalid")
        previous = descriptor.get("previous_descriptor_sha256")
        if previous is not None and not re.fullmatch(r"[0-9a-f]{64}", str(previous)):
            raise ApplicationAccountRecoveryError("application_account_descriptor_previous_digest_invalid")
        if expected_previous_descriptor_sha256 and not hmac.compare_digest(
            str(previous or ""), str(expected_previous_descriptor_sha256)
        ):
            raise PermissionError("application_account_descriptor_continuity_invalid")
        return {
            **descriptor,
            "workspace_id": workspace,
            "recovery_epoch": epoch,
            "active_devices": clean_devices,
            "signature_base64": signature_encoded,
        }

    @classmethod
    def _account_id(cls, public_bytes: bytes) -> str:
        return "account_" + sha256(public_bytes).hexdigest()[:40]

    def _signed_descriptor(
        self,
        private_key: Ed25519PrivateKey,
        *,
        account_id: str,
        workspace_id: str,
        epoch: int,
        active_devices: list[str],
        previous_descriptor_sha256: str | None,
        event_type: str,
        event_actor_hash: str,
    ) -> dict[str, Any]:
        body = {
            "schema_version": self.DESCRIPTOR_SCHEMA,
            "account_id": account_id,
            "workspace_id": workspace_id,
            "root_public_key_base64": base64.b64encode(
                private_key.public_key().public_bytes_raw()
            ).decode("ascii"),
            "recovery_epoch": int(epoch),
            "active_devices": list(active_devices),
            "previous_descriptor_sha256": previous_descriptor_sha256,
            "event_type": event_type,
            "event_actor_sha256": event_actor_hash,
            "issued_at": _utc_now(),
            "all_unlisted_devices_revoked": True,
        }
        return {
            **body,
            "signature_base64": base64.b64encode(private_key.sign(_canonical(body))).decode("ascii"),
        }

    def _off_device_kit_path(self, value: str | Path) -> Path:
        path = Path(value).expanduser().resolve()
        if path == self.root or self.root in path.parents:
            raise ApplicationAccountRecoveryError("account_recovery_kit_must_be_stored_off_device_runtime")
        if path.is_symlink():
            raise ApplicationAccountRecoveryError("account_recovery_kit_path_unsafe")
        return path

    def _encrypt_kit(
        self,
        *,
        password: str,
        account_id: str,
        workspace_id: str,
        public_key: bytes,
        private_key: bytes,
    ) -> dict[str, Any]:
        payload = {
            "schema_version": self.KIT_SCHEMA,
            "account_id": account_id,
            "workspace_id": workspace_id,
            "root_public_key_base64": base64.b64encode(public_key).decode("ascii"),
            "root_private_key_base64": base64.b64encode(private_key).decode("ascii"),
            "created_at": _utc_now(),
        }
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        header = {
            "schema_version": self.KIT_ENVELOPE_SCHEMA,
            "kdf": "scrypt-n32768-r8-p1",
            "cipher": "AES-256-GCM",
            "account_id": account_id,
            "workspace_id": workspace_id,
        }
        key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode("utf-8"))
        ciphertext = AESGCM(key).encrypt(nonce, _canonical(payload), _canonical(header))
        return {
            "header": header,
            "salt_base64": base64.b64encode(salt).decode("ascii"),
            "nonce_base64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_base64": base64.b64encode(ciphertext).decode("ascii"),
        }

    def _decrypt_kit(self, kit: Mapping[str, Any], *, password: str) -> dict[str, Any]:
        header = dict(kit.get("header") or {})
        if (
            header.get("schema_version") != self.KIT_ENVELOPE_SCHEMA
            or header.get("kdf") != "scrypt-n32768-r8-p1"
            or header.get("cipher") != "AES-256-GCM"
        ):
            raise ApplicationAccountRecoveryError("account_recovery_kit_header_invalid")
        try:
            salt = base64.b64decode(str(kit["salt_base64"]), validate=True)
            nonce = base64.b64decode(str(kit["nonce_base64"]), validate=True)
            ciphertext = base64.b64decode(str(kit["ciphertext_base64"]), validate=True)
            if len(salt) != 16 or len(nonce) != 12:
                raise ValueError
            key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode("utf-8"))
            payload = json.loads(AESGCM(key).decrypt(nonce, ciphertext, _canonical(header)))
            private_key = base64.b64decode(str(payload["root_private_key_base64"]), validate=True)
            public_key = base64.b64decode(str(payload["root_public_key_base64"]), validate=True)
        except Exception:
            raise PermissionError("Application-account recovery kit could not be authenticated") from None
        if payload.get("schema_version") != self.KIT_SCHEMA or len(private_key) != 32 or len(public_key) != 32:
            raise ApplicationAccountRecoveryError("account_recovery_kit_payload_invalid")
        for field in ("account_id", "workspace_id"):
            if not hmac.compare_digest(str(payload.get(field) or ""), str(header.get(field) or "")):
                raise PermissionError("account_recovery_kit_header_payload_mismatch")
        return {
            "account_id": str(payload["account_id"]),
            "workspace_id": _component(str(payload["workspace_id"]), "workspace_id"),
            "private_key": private_key,
            "public_key": public_key,
        }

    def _read_kit(self, value: str | Path) -> dict[str, Any]:
        path = Path(value).expanduser().resolve()
        if not path.is_file() or path.is_symlink() or path.stat().st_size > self.MAX_KIT_BYTES:
            raise ApplicationAccountRecoveryError("account_recovery_kit_missing_or_unsafe")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ApplicationAccountRecoveryError("account_recovery_kit_unreadable") from exc
        if not isinstance(value, dict):
            raise ApplicationAccountRecoveryError("account_recovery_kit_invalid")
        return value

    def _write_kit(self, path: Path, kit: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        encoded = _canonical(dict(kit))
        if len(encoded) > self.MAX_KIT_BYTES:
            raise ApplicationAccountRecoveryError("account_recovery_kit_too_large")
        temporary.write_bytes(encoded)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def _write_descriptor(self, descriptor: Mapping[str, Any]) -> None:
        self.verify_descriptor(descriptor)
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_bytes(_canonical(dict(descriptor)))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.state_path)

    def _store_root_key(self, account_id: str, private_bytes: bytes) -> None:
        if len(private_bytes) != 32:
            raise ApplicationAccountRecoveryError("account_recovery_root_key_invalid")
        account = f"root:{account_id}"
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring

                existing = str(keyring.get_password(self.SERVICE, account) or "").strip()
                if existing and not hmac.compare_digest(
                    base64.b64decode(existing, validate=True), private_bytes
                ):
                    raise RuntimeError("different_account_root_exists")
                keyring.set_password(self.SERVICE, account, base64.b64encode(private_bytes).decode("ascii"))
                return
            except Exception as exc:
                raise RuntimeError("Application-account production Keychain is unavailable") from exc
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        if self.development_key_path.exists() and not hmac.compare_digest(
            self.development_key_path.read_bytes(), private_bytes
        ):
            raise RuntimeError("A different application-account root already exists")
        temporary = self.development_key_path.with_suffix(".tmp")
        temporary.write_bytes(private_bytes)
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.development_key_path)

    @classmethod
    def _validate_password(cls, password: str) -> None:
        if len(str(password)) < cls.MIN_PASSWORD_CHARS:
            raise ApplicationAccountRecoveryError("account_recovery_password_minimum_16_characters")
