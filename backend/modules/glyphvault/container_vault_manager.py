# backend/modules/glyphvault/container_vault_manager.py

import json
import logging
from typing import Optional
from backend.modules.glyphvault.glyph_encryptor import GlyphEncryptor
from backend.modules.glyphos.microgrid_index import MicrogridIndex

logger = logging.getLogger(__name__)

class ContainerVaultManager:
    """
    Manages encrypted glyph data vaults for .dc containers.
    Handles serialization, encryption, decryption, and loading glyph metadata into MicrogridIndex.
    """

    def __init__(self, encryption_key: bytes):
        self.encryptor = GlyphEncryptor(encryption_key)
        self.microgrid = MicrogridIndex()

    def save_container_glyph_data(self, glyph_data: dict, associated_data: Optional[bytes] = None) -> bytes:
        """
        Serialize and encrypt glyph data dict for storage.

        Args:
            glyph_data (dict): Glyph metadata map (coordinate keys -> metadata)
            associated_data (bytes): Optional additional data to authenticate

        Returns:
            bytes: Encrypted container glyph data blob
        """
        try:
            serialized = json.dumps(glyph_data).encode("utf-8")
            encrypted = self.encryptor.encrypt(serialized, associated_data)
            logger.info(f"Encrypted glyph data of size {len(serialized)} bytes")
            return encrypted
        except Exception as e:
            logger.error(f"Failed to encrypt container glyph data: {e}")
            raise

    def load_container_glyph_data(self, encrypted_blob: bytes, associated_data: Optional[bytes] = None,
                                  avatar_state: Optional[dict] = None) -> bool:
        """
        Decrypt and import glyph data into MicrogridIndex.

        Args:
            encrypted_blob (bytes): Encrypted glyph data
            associated_data (bytes): Optional additional authenticated data
            avatar_state (dict): Avatar state for access control checks

        Returns:
            bool: True if successful, False otherwise
        """
        plaintext = self.encryptor.decrypt(encrypted_blob, associated_data, avatar_state)
        if plaintext is None:
            logger.warning("Decryption failed or access denied by avatar state")
            return False
        try:
            glyph_data = json.loads(plaintext.decode("utf-8"))
            self.microgrid.import_index(glyph_data)
            logger.info(f"Imported {len(glyph_data)} glyphs into microgrid index")
            return True
        except Exception as e:
            logger.error(f"Failed to deserialize glyph data: {e}")
            return False

    def get_microgrid(self) -> MicrogridIndex:
        """Return the MicrogridIndex instance with loaded glyph data."""
        return self.microgrid