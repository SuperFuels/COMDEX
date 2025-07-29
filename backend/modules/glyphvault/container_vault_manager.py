# backend/modules/glyphvault/container_vault_manager.py

import json
import logging
from typing import Optional
from backend.modules.glyphvault.glyph_encryptor import GlyphEncryptor
from backend.modules.glyphos.microgrid_index import MicrogridIndex
from backend.modules.soullaw.soul_law_validator import soul_law_validator  # ✅ SoulLaw validation
from backend.modules.knowledge.knowledge_graph_writer import KnowledgeGraphWriter  # ✅ KG logging
from backend.modules.ucs.ucs_runtime import get_ucs_runtime  # ✅ UCS sync for vault ops

logger = logging.getLogger(__name__)

class ContainerVaultManager:
    """
    Manages encrypted glyph data vaults for .dc containers.
    Handles serialization, encryption, decryption, and loading glyph metadata into MicrogridIndex.
    Includes SoulLaw validation, KG logging, and UCS integration.
    """

    def __init__(self, encryption_key: bytes):
        self.encryptor = GlyphEncryptor(encryption_key)
        self.microgrid = MicrogridIndex()
        self.kg_writer = KnowledgeGraphWriter()

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
            # ✅ Validate via SoulLaw before encryption
            self._validate_glyph_data_soullaw(glyph_data)

            serialized = json.dumps(glyph_data).encode("utf-8")
            encrypted = self.encryptor.encrypt(serialized, associated_data)
            logger.info(f"[Vault] Encrypted glyph data of size {len(serialized)} bytes")

            # ✅ KG Logging
            self.kg_writer.inject_glyph(
                content=f"Encrypted {len(glyph_data)} glyphs into vault.",
                glyph_type="vault_event",
                metadata={"tags": ["vault", "encrypt"]},
                plugin="VaultManager"
            )

            return encrypted
        except Exception as e:
            logger.error(f"[Vault] Failed to encrypt container glyph data: {e}")
            self.kg_writer.inject_glyph(
                content=f"Vault encryption failed: {str(e)}",
                glyph_type="error",
                metadata={"tags": ["vault", "error"]},
                plugin="VaultManager"
            )
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
            logger.warning("[Vault] Decryption failed or access denied by avatar state")
            self.kg_writer.inject_glyph(
                content="Vault decryption denied by SoulLaw/identity mismatch.",
                glyph_type="violation",
                metadata={"tags": ["vault", "soullaw", "denied"]},
                plugin="VaultManager"
            )
            return False

        try:
            glyph_data = json.loads(plaintext.decode("utf-8"))

            # ✅ Validate glyphs against SoulLaw before import
            self._validate_glyph_data_soullaw(glyph_data)

            self.microgrid.import_index(glyph_data)
            logger.info(f"[Vault] Imported {len(glyph_data)} glyphs into microgrid index")

            # ✅ KG Logging
            self.kg_writer.inject_glyph(
                content=f"Decrypted and imported {len(glyph_data)} glyphs from vault.",
                glyph_type="vault_event",
                metadata={"tags": ["vault", "decrypt"]},
                plugin="VaultManager"
            )

            # ✅ UCS Sync: Register microgrid state
            ucs = get_ucs_runtime()
            ucs.sync_microgrid(self.microgrid)

            return True
        except Exception as e:
            logger.error(f"[Vault] Failed to deserialize glyph data: {e}")
            self.kg_writer.inject_glyph(
                content=f"Vault glyph import failed: {str(e)}",
                glyph_type="error",
                metadata={"tags": ["vault", "error"]},
                plugin="VaultManager"
            )
            return False

    def get_microgrid(self) -> MicrogridIndex:
        """Return the MicrogridIndex instance with loaded glyph data."""
        return self.microgrid

    def _validate_glyph_data_soullaw(self, glyph_data: dict):
        """
        Validate glyph metadata against SoulLaw.
        """
        for coord, meta in glyph_data.items():
            glyph = meta.get("glyph")
            if glyph and not soul_law_validator.validate_container({"glyph": glyph}):
                logger.warning(f"[Vault] SoulLaw violation detected for glyph at {coord}: {glyph}")
                self.kg_writer.inject_soullaw_violation(
                    rule="glyph_validation",
                    reason=f"Rejected glyph {glyph} at {coord}",
                    context={"coord": coord, "glyph": glyph}
                )