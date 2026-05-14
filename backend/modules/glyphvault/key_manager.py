import os
import logging

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Centralized encryption key manager for GlyphVault.

    - Loads key securely from environment variable or file.
    - Tracks the Vault public identity for attribution.
    - Provides a safe default for development/testing only.
    """

    # Default fallback key for testing only (32 bytes)
    DEFAULT_TEST_KEY = b"0123456789abcdef0123456789abcdef"

    def __init__(self):
        self._key = None
        self._public_id = os.getenv("GLYPHVAULT_PUBLIC_ID") or "VAULT://unknown"
        self.load_key()

    def load_key(self):
        """
        Load the encryption key in the following priority:
        1. Environment variable: GLYPHVAULT_ENCRYPTION_KEY_HEX
        2. File path from env: GLYPHVAULT_KEY_FILE
        3. Fallback to default test key (⚠️ not secure)
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
                logger.info(f"GlyphVault encryption key loaded from file: {key_file}")
                return
            except Exception as e:
                logger.error(f"Failed to load GlyphVault encryption key from file {key_file}: {e}")
                self._key = None

        # Fallback warning
        if self._key is None:
            logger.warning("⚠️ Using fallback default encryption key (NOT SECURE, dev/test only)")
            self._key = self.DEFAULT_TEST_KEY

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