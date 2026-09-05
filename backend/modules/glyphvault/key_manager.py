import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Centralized encryption key manager for GlyphVault.

    - Loads key securely from environment variable or file.
    - Tracks the Vault public identity for attribution.
    - Generates a unique owner-only development key when no explicit key exists.
    - Requires an explicit customer keystore binding in production.
    """

    KEYCHAIN_SERVICE = "ai.tessaris.glyphvault"

    def __init__(self, *, runtime_mode: str | None = None, development_key_file: str | None = None):
        self._key = None
        self._public_id = os.getenv("GLYPHVAULT_PUBLIC_ID") or "VAULT://unknown"
        self._runtime_mode = str(runtime_mode or os.getenv("TESSARIS_RUNTIME_MODE") or "development").strip().lower()
        self._development_key_file = Path(development_key_file or os.getenv("GLYPHVAULT_DEVELOPMENT_KEY_FILE") or Path.home() / ".tessaris/security/glyphvault-development.key")
        self._source = ""
        self.load_key()

    def load_key(self):
        """
        Load the encryption key in the following priority:
        1. Environment variable: GLYPHVAULT_ENCRYPTION_KEY_HEX
        2. File path from env: GLYPHVAULT_KEY_FILE
        3. Platform keychain in production.
        4. A unique owner-only file in development/test only.
        """
        key_hex = os.getenv("GLYPHVAULT_ENCRYPTION_KEY_HEX")
        key_file = os.getenv("GLYPHVAULT_KEY_FILE")

        if key_hex:
            logger.debug("Loading GlyphVault encryption key from environment...")
            try:
                key_bytes = bytes.fromhex(key_hex)
                if len(key_bytes) != 32:
                    raise ValueError("Encryption key must be exactly 32 bytes (256 bits)")
                self._key = key_bytes
                self._source = "environment"
                logger.info("GlyphVault encryption key loaded from environment")
                return
            except Exception as e:
                logger.error(f"Failed to parse GlyphVault encryption key from env: {e}")
                self._key = None

        if key_file:
            try:
                with open(key_file, "rb") as f:
                    key_bytes = f.read().strip()
                if len(key_bytes) == 64:  # hex string in file
                    key_bytes = bytes.fromhex(key_bytes.decode())
                if len(key_bytes) != 32:
                    raise ValueError("Key file must contain 32 raw bytes or 64 hex chars")
                self._key = key_bytes
                self._source = "configured_file"
                logger.info(f"GlyphVault encryption key loaded from file: {key_file}")
                return
            except Exception as e:
                logger.error(f"Failed to load GlyphVault encryption key from file {key_file}: {e}")
                self._key = None

        if self._runtime_mode in {"production", "prod"}:
            try:
                import keyring
                encoded = str(keyring.get_password(self.KEYCHAIN_SERVICE, self._public_id) or "").strip()
                if encoded:
                    candidate = bytes.fromhex(encoded)
                    if len(candidate) != 32:
                        raise ValueError("Customer keystore key must be 32 bytes")
                    self._key = candidate
                    self._source = "platform_keychain"
                    return
            except Exception as exc:
                logger.error("GlyphVault production keystore lookup failed: %s", exc)
            raise RuntimeError("GlyphVault customer keystore key is required in production")

        self._development_key_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self._development_key_file.parent, 0o700)
        except OSError:
            pass
        if not self._development_key_file.exists():
            self._development_key_file.write_bytes(os.urandom(32))
            os.chmod(self._development_key_file, 0o600)
        candidate = self._development_key_file.read_bytes()
        if len(candidate) != 32:
            raise RuntimeError("GlyphVault development key file is invalid")
        self._key = candidate
        self._source = "unique_development_device_file"
        logger.info("GlyphVault loaded a unique local development key; no shared fallback key is in use")

    @property
    def key(self) -> bytes:
        """Returns the loaded encryption key (32 bytes)."""
        if self._key is None:
            raise RuntimeError("Encryption key not loaded or invalid")
        return self._key

    @property
    def public_id(self) -> str:
        """
        Returns the Vault public identity (used in signature_block["signer"]).
        """
        return self._public_id

    @property
    def source(self) -> str:
        return self._source

# ✅ Singleton instance
key_manager = KeyManager()

def get_encryption_key(*args, **kwargs) -> bytes:
    """
    Compatibility shim for StateManager and other legacy callers.
    Ignores optional kwargs like `default_fallback`.
    Returns the active encryption key from the singleton KeyManager.
    """
    return key_manager.key


def get_vault_public_id() -> str:
    """
    Compatibility shim to expose the Vault public identity.
    """
    return key_manager.public_id
