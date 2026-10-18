from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


@dataclass(slots=True)
class DeviceIdentity:
    private_key: Ed25519PrivateKey

    @property
    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_key_b64(self) -> str:
        return base64.b64encode(self.public_key_bytes).decode("ascii")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.public_key_bytes).hexdigest()[:32]

    def sign(self, payload: bytes) -> str:
        return base64.b64encode(self.private_key.sign(payload)).decode("ascii")

    @staticmethod
    def verify(public_key_b64: str, payload: bytes, signature_b64: str) -> bool:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
            public_key.verify(base64.b64decode(signature_b64), payload)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False


class IdentityStore:
    """Persist device identity separately from runtime and cognitive data."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self.private_path = self.directory / "device_ed25519.pem"
        self.public_path = self.directory / "device_ed25519.pub"

    def load_or_create(self) -> DeviceIdentity:
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.private_path.exists():
            private_key = serialization.load_pem_private_key(
                self.private_path.read_bytes(),
                password=None,
            )
            if not isinstance(private_key, Ed25519PrivateKey):
                raise ValueError("AION Fabric identity is not an Ed25519 key")
            return DeviceIdentity(private_key)

        identity = DeviceIdentity(Ed25519PrivateKey.generate())
        private_bytes = identity.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.private_path.write_bytes(private_bytes)
        os.chmod(self.private_path, 0o600)
        self.public_path.write_text(identity.public_key_b64 + "\n", encoding="utf-8")
        os.chmod(self.public_path, 0o644)
        return identity
