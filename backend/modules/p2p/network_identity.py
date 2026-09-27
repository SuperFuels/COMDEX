"""Versioned GlyphChain P2P transport identity with rotation and encrypted recovery."""

from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import threading
from typing import Any, Callable, Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.p2p.crypto_ed25519 import pubkey_from_priv, sign_ed25519, stable_json_bytes, verify_ed25519


class NetworkIdentityError(ValueError):
    pass


class NetworkIdentityStore:
    SERVICE = "ai.tessaris.glyphchain"
    SCHEMA_VERSION = "glyphchain.network-identity.v1"
    ROTATION_SCHEMA = "glyphchain.network-key-rotation.v1"
    RECOVERY_SCHEMA = "glyphchain.network-key-recovery.v1"
    CONFIRMATION = "ROTATE GLYPHCHAIN NETWORK KEY"

    def __init__(
        self,
        root: str | Path,
        *,
        chain_id: str,
        node_id: str,
        runtime_mode: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root)
        self.path = self.root / "network-identity.json"
        self.chain_id = self._component(chain_id, "chain_id")
        self.node_id = self._component(node_id, "node_id")
        self.runtime_mode = str(runtime_mode or os.getenv("TESSARIS_RUNTIME_MODE") or "development").lower()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()

    def identity(self) -> dict[str, Any]:
        with self._lock:
            state = self._state(create=True)
            version = int(state["active_version"])
            private = self._private(version)
            public = pubkey_from_priv(private.hex())
            expected = str(state["public_keys"].get(str(version)) or "")
            if expected and expected != public:
                raise NetworkIdentityError("network_identity_public_key_mismatch")
            if not expected:
                state["public_keys"][str(version)] = public
                self._write(state)
            return {
                "schema_version": self.SCHEMA_VERSION,
                "chain_id": self.chain_id,
                "node_id": self.node_id,
                "active_version": version,
                "public_key_hex": public,
                "key_id": f"ed25519:sha256:{sha256(bytes.fromhex(public)).hexdigest()}",
                "key_source": "platform_keychain" if self.runtime_mode in {"production", "prod"} else "owner_only_development_file",
                "retained_key_versions": len(state["public_keys"]),
                "rotation_count": len(state["rotations"]),
                "raw_private_key_exposed": False,
            }

    def active_private_key_hex(self) -> str:
        state = self._state(create=True)
        return self._private(int(state["active_version"])).hex()

    def rotate(self, *, actor_id: str, reason: str, confirmation: str) -> dict[str, Any]:
        actor = str(actor_id or "").strip()
        why = str(reason or "").strip()
        if confirmation != self.CONFIRMATION:
            raise NetworkIdentityError("network_key_rotation_confirmation_required")
        if not actor or not why:
            raise NetworkIdentityError("network_key_rotation_actor_and_reason_required")
        with self._lock:
            state = self._state(create=True)
            old_version = int(state["active_version"])
            old_private = self._private(old_version)
            old_public = pubkey_from_priv(old_private.hex())
            new_version = old_version + 1
            new_private = Ed25519PrivateKey.generate().private_bytes_raw()
            self._store_private(new_version, new_private, allow_existing=False)
            new_public = pubkey_from_priv(new_private.hex())
            previous_hash = state["rotations"][-1]["rotation_hash"] if state["rotations"] else None
            certificate = {
                "schema_version": self.ROTATION_SCHEMA,
                "chain_id": self.chain_id,
                "node_id": self.node_id,
                "sequence": len(state["rotations"]) + 1,
                "old_key_version": old_version,
                "old_public_key_hex": old_public,
                "new_key_version": new_version,
                "new_public_key_hex": new_public,
                "rotated_at": self.clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "rotated_by": actor[:160],
                "reason": why[:1000],
                "previous_rotation_hash": previous_hash,
            }
            sign_bytes = stable_json_bytes(certificate)
            certificate["old_key_signature_hex"] = sign_ed25519(old_private.hex(), sign_bytes)
            certificate["new_key_signature_hex"] = sign_ed25519(new_private.hex(), sign_bytes)
            certificate["rotation_hash"] = sha256(stable_json_bytes(certificate)).hexdigest()
            state["active_version"] = new_version
            state["public_keys"][str(new_version)] = new_public
            state["rotations"].append(certificate)
            self._write(state)
        return {"identity": self.identity(), "rotation_certificate": deepcopy(certificate), "restart_required": True}

    def verify_rotation_chain(self) -> bool:
        state = self._state(create=False)
        return self._verify_rotation_state(state)

    def _verify_rotation_state(self, state: Mapping[str, Any]) -> bool:
        previous_hash = None
        previous_new = None
        for index, certificate in enumerate(state["rotations"], start=1):
            item = dict(certificate)
            supplied_hash = str(item.pop("rotation_hash", ""))
            if supplied_hash != sha256(stable_json_bytes(item)).hexdigest():
                return False
            old_signature = str(item.pop("old_key_signature_hex", ""))
            new_signature = str(item.pop("new_key_signature_hex", ""))
            if item.get("schema_version") != self.ROTATION_SCHEMA or int(item.get("sequence") or 0) != index:
                return False
            if item.get("chain_id") != self.chain_id or item.get("node_id") != self.node_id:
                return False
            if item.get("previous_rotation_hash") != previous_hash:
                return False
            if previous_new and item.get("old_public_key_hex") != previous_new:
                return False
            sign_bytes = stable_json_bytes(item)
            if not verify_ed25519(str(item.get("old_public_key_hex") or ""), old_signature, sign_bytes):
                return False
            if not verify_ed25519(str(item.get("new_public_key_hex") or ""), new_signature, sign_bytes):
                return False
            previous_hash = supplied_hash
            previous_new = item.get("new_public_key_hex")
        return True

    def export_recovery_bundle(self, password: str) -> dict[str, Any]:
        if len(str(password)) < 12:
            raise NetworkIdentityError("network_recovery_password_minimum_12_characters")
        state = self._state(create=True)
        payload = {
            "schema_version": self.RECOVERY_SCHEMA,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "state": state,
            "private_keys": {version: base64.b64encode(self._private(int(version))).decode("ascii")
                             for version in state["public_keys"]},
        }
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(str(password).encode())
        header = {"schema_version": "glyphchain.network-key-recovery-envelope.v1", "kdf": "scrypt-n16384-r8-p1", "cipher": "AES-256-GCM"}
        encrypted = AESGCM(key).encrypt(nonce, stable_json_bytes(payload), stable_json_bytes(header))
        return {"header": header, "salt_base64": base64.b64encode(salt).decode(),
                "nonce_base64": base64.b64encode(nonce).decode(), "ciphertext_base64": base64.b64encode(encrypted).decode(),
                "raw_private_keys_exposed": False}

    def import_recovery_bundle(self, package: Mapping[str, Any], password: str) -> dict[str, Any]:
        if len(str(password)) < 12:
            raise NetworkIdentityError("network_recovery_password_minimum_12_characters")
        header = dict(package.get("header") or {})
        expected = {"schema_version": "glyphchain.network-key-recovery-envelope.v1", "kdf": "scrypt-n16384-r8-p1", "cipher": "AES-256-GCM"}
        if header != expected:
            raise NetworkIdentityError("network_recovery_header_invalid")
        try:
            salt = base64.b64decode(str(package["salt_base64"]), validate=True)
            nonce = base64.b64decode(str(package["nonce_base64"]), validate=True)
            ciphertext = base64.b64decode(str(package["ciphertext_base64"]), validate=True)
            key = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(str(password).encode())
            payload = json.loads(AESGCM(key).decrypt(nonce, ciphertext, stable_json_bytes(header)))
        except Exception:
            raise PermissionError("GlyphChain network recovery bundle could not be authenticated") from None
        if payload.get("schema_version") != self.RECOVERY_SCHEMA or payload.get("chain_id") != self.chain_id or payload.get("node_id") != self.node_id:
            raise NetworkIdentityError("network_recovery_identity_mismatch")
        state = dict(payload.get("state") or {})
        keys = dict(payload.get("private_keys") or {})
        self._validate_state(state)
        if not self._verify_rotation_state(state):
            raise NetworkIdentityError("network_recovery_rotation_chain_invalid")
        for version, public in dict(state.get("public_keys") or {}).items():
            try:
                private = base64.b64decode(str(keys[version]), validate=True)
            except Exception:
                raise NetworkIdentityError("network_recovery_key_missing_or_invalid") from None
            if len(private) != 32 or pubkey_from_priv(private.hex()) != public:
                raise NetworkIdentityError("network_recovery_key_mismatch")
            self._store_private(int(version), private, allow_existing=True)
        self._write(state)
        return {"restored_key_versions": len(keys), "active_version": state["active_version"],
                "raw_private_keys_exposed": False, "restart_required": True}

    def _state(self, *, create: bool) -> dict[str, Any]:
        if self.path.exists():
            try:
                state = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise NetworkIdentityError("network_identity_state_unreadable") from exc
            return self._validate_state(state)
        if not create:
            return {"schema_version": self.SCHEMA_VERSION, "chain_id": self.chain_id, "node_id": self.node_id,
                    "active_version": 1, "public_keys": {}, "rotations": []}
        private = Ed25519PrivateKey.generate().private_bytes_raw()
        self._store_private(1, private, allow_existing=True)
        state = {"schema_version": self.SCHEMA_VERSION, "chain_id": self.chain_id, "node_id": self.node_id,
                 "active_version": 1, "public_keys": {"1": pubkey_from_priv(private.hex())}, "rotations": []}
        self._write(state)
        return state

    def _validate_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
        value = deepcopy(dict(state))
        if value.get("schema_version") != self.SCHEMA_VERSION or value.get("chain_id") != self.chain_id or value.get("node_id") != self.node_id:
            raise NetworkIdentityError("network_identity_state_invalid")
        if not isinstance(value.get("public_keys"), dict) or not isinstance(value.get("rotations"), list):
            raise NetworkIdentityError("network_identity_state_invalid")
        if len(value["public_keys"]) > 10_000 or len(value["rotations"]) > 10_000:
            raise NetworkIdentityError("network_identity_history_limit_exceeded")
        if any(not re.fullmatch(r"[0-9a-f]{64}", str(public or "")) for public in value["public_keys"].values()):
            raise NetworkIdentityError("network_identity_public_key_invalid")
        active = int(value.get("active_version") or 0)
        if active < 1 or str(active) not in value["public_keys"]:
            raise NetworkIdentityError("network_identity_active_key_invalid")
        return value

    def _private(self, version: int) -> bytes:
        account = f"p2p-transport:{self.chain_id}:{self.node_id}:v{version}"
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring
                encoded = keyring.get_password(self.SERVICE, account)
                if not encoded:
                    raise RuntimeError("missing")
                value = base64.b64decode(encoded, validate=True)
            except Exception as exc:
                raise RuntimeError("GlyphChain production Keychain is unavailable or missing the network identity") from exc
        else:
            path = self.root / "_secure_keys" / f"v{version}.key"
            if not path.exists():
                raise NetworkIdentityError("network_private_key_missing")
            value = path.read_bytes()
        if len(value) != 32:
            raise NetworkIdentityError("network_private_key_invalid")
        return value

    def _store_private(self, version: int, value: bytes, *, allow_existing: bool) -> None:
        if len(value) != 32:
            raise NetworkIdentityError("network_private_key_invalid")
        account = f"p2p-transport:{self.chain_id}:{self.node_id}:v{version}"
        if self.runtime_mode in {"production", "prod"}:
            try:
                import keyring
                existing = keyring.get_password(self.SERVICE, account)
                if existing and base64.b64decode(existing, validate=True) != value:
                    raise NetworkIdentityError("network_private_key_conflict")
                keyring.set_password(self.SERVICE, account, base64.b64encode(value).decode())
            except NetworkIdentityError:
                raise
            except Exception as exc:
                raise RuntimeError("GlyphChain production Keychain is unavailable") from exc
            return
        folder = self.root / "_secure_keys"; folder.mkdir(parents=True, exist_ok=True)
        try: os.chmod(folder, 0o700)
        except OSError: pass
        path = folder / f"v{version}.key"
        if path.exists():
            if path.read_bytes() != value:
                raise NetworkIdentityError("network_private_key_conflict")
            if allow_existing:
                return
            raise NetworkIdentityError("network_private_key_already_exists")
        temporary = path.with_suffix(".tmp"); temporary.write_bytes(value)
        try: os.chmod(temporary, 0o600)
        except OSError: pass
        os.replace(temporary, path)

    def _write(self, state: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try: os.chmod(self.root, 0o700)
        except OSError: pass
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(dict(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try: os.chmod(temporary, 0o600)
        except OSError: pass
        os.replace(temporary, self.path)

    @staticmethod
    def _component(value: str, field: str) -> str:
        clean = str(value or "").strip()
        if not clean or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,180}", clean):
            raise NetworkIdentityError(f"network_identity_{field}_invalid")
        return clean
