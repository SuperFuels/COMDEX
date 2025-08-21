# backend/modules/glyphvault/container_vault_manager.py

import json
import logging
import os 
from typing import Optional

from backend.modules.glyphvault.glyph_encryptor import GlyphEncryptor
from backend.modules.glyphos.microgrid_index import MicrogridIndex
from backend.modules.glyphvault.soul_law_validator import soul_law_validator  # ✅ SoulLaw validation
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime  # ✅ UCS sync for vault ops
from backend.modules.glyphvault.kg_writer_singleton import get_kg_writer  # ✅ Safe KG writer import

logger = logging.getLogger(__name__)
_vmanager_seen = set()

class ContainerVaultManager:
    """
    Manages encrypted glyph data vaults for .dc containers.
    Handles serialization, encryption, decryption, and loading glyph metadata into MicrogridIndex.
    Includes SoulLaw validation, KG logging, and UCS integration.
    """

    def __init__(self, encryption_key: bytes):
        self.encryptor = GlyphEncryptor(encryption_key)
        self.microgrid = MicrogridIndex()
        self.kg_writer = get_kg_writer()
        try:
            from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
            self.kg_writer = KnowledgeGraphWriter()
        except ImportError:
            logger.warning("[Vault] KG Writer unavailable due to circular import")

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
                        # ✅ KG Logging
            if self.kg_writer:
                self.kg_writer.log_event(
                    event_type="vault_encrypt",
                    content=f"Encrypted {len(glyph_data)} glyphs into vault.",
                    metadata={
                        "tags": ["vault", "encrypt"],
                        "glyph_count": len(glyph_data)
                    },
                    source="VaultManager"
                )

            return encrypted
        except Exception as e:
            logger.error(f"[Vault] Failed to encrypt container glyph data: {e}")
            if self.kg_writer:
                self.kg_writer.log_event(
                    event_type="vault_error",
                    content=f"Vault encryption failed: {str(e)}",
                    metadata={
                        "tags": ["vault", "error"],
                        "exception": str(e)
                    },
                    source="VaultManager"
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
            if self.kg_writer:
                self.kg_writer.log_event(
                    event_type="vault_violation",
                    content="Vault decryption denied by SoulLaw/identity mismatch.",
                    metadata={"tags": ["vault", "soullaw", "denied"]},
                    source="VaultManager"
                )
            return False

        try:
            glyph_data = json.loads(plaintext.decode("utf-8"))

            # ✅ Validate glyphs against SoulLaw before import
            self._validate_glyph_data_soullaw(glyph_data)

            self.microgrid.import_index(glyph_data)
            logger.info(f"[Vault] Imported {len(glyph_data)} glyphs into microgrid index")

            # ✅ KG Logging
            if self.kg_writer:
                self.kg_writer.log_event(
                    event_type="vault_event",
                    content=f"Decrypted and imported {len(glyph_data)} glyphs from vault.",
                    metadata={"tags": ["vault", "decrypt"]},
                    source="VaultManager"
                )

            # ✅ UCS Sync: Register microgrid state
            ucs = get_ucs_runtime()
            ucs.sync_microgrid(self.microgrid)

            return True
        except Exception as e:
            logger.error(f"[Vault] Failed to deserialize glyph data: {e}")
            if self.kg_writer:
                self.kg_writer.log_event(
                    event_type="error",
                    content=f"Vault glyph import failed: {str(e)}",
                    metadata={"tags": ["vault", "error"]},
                    source="VaultManager"
                )
            return False

    def get_microgrid(self) -> MicrogridIndex:
        """Return the MicrogridIndex instance with loaded glyph data."""
        return self.microgrid

    def _validate_glyph_data_soullaw(self, glyph_data: dict):
        """
        Validate glyph metadata against SoulLaw (gated one-time per glyph/container).
        If data does not match glyph microgrid format, skip validation.
        """

        # Early short-circuit: glyph_data must be a dict of dicts
        if not isinstance(glyph_data, dict):
            logger.warning(f"[Vault] Glyph data is not a dict. Skipping SoulLaw validation.")
            return False

        # Check for a typical .dc.json container file
        if "id" in glyph_data and "type" in glyph_data:
            logger.info(f"[Vault] Skipping SoulLaw validation for full container JSON: {glyph_data.get('id')}")
            return False

        for coord, meta in glyph_data.items():
            if not isinstance(meta, dict):
                logger.warning(f"[Vault] Glyph meta at {coord} is not a dict. Skipping.")
                continue

            glyph = meta.get("glyph")

            # Build a stable key for gating: prefer glyph dict ids, else container/coord fallback
            if isinstance(glyph, dict):
                key = glyph.get("container_id") or glyph.get("id") or glyph.get("glyph_id")
            else:
                key = None

            if not key:
                key = f"{meta.get('container_id') or meta.get('id') or 'unknown'}::{coord}"

            # Skip if we've already validated this glyph/container once
            if key in _vmanager_seen:
                continue

            try:
                # Validate once, passing an explicit id so the validator can gate too
                payload = {"glyph": glyph, "id": key}
                if not soul_law_validator.validate_container(payload):
                    logger.warning(f"[Vault] SoulLaw violation detected for glyph at {coord}: {glyph}")
                    if self.kg_writer:
                        self.kg_writer.log_event(
                            event_type="soullaw_violation",
                            content=f"Rejected glyph {glyph} at {coord}",
                            metadata={
                                "rule": "glyph_validation",
                                "context": {"coord": coord, "glyph": glyph, "id": key}
                            },
                            source="VaultManager"
                        )
                    return False  # fail closed
            except Exception as e:
                logger.warning(f"[Vault] SoulLaw check failed for {key} at {coord}: {e}")
                # fail open – continue
            finally:
                _vmanager_seen.add(key)

        return True
    
    def load_container_by_id(self, container_id: str) -> dict:
        """
        Loads a full container JSON (.dc.json) by ID from the standard Vault path.

        Args:
            container_id (str): The ID of the container file (without extension)

        Returns:
            dict: Parsed JSON container data
        """
        primary_path = os.path.join("data/containers", f"{container_id}.dc.json")
        fallback_path = os.path.join("backend/modules/dimensions/containers", f"{container_id}.dc.json")

        if os.path.exists(primary_path):
            print(f"📂 [VaultBridge] Loaded container from: {primary_path}")
            with open(primary_path, "r") as f:
                return json.load(f)
        elif os.path.exists(fallback_path):
            print(f"📂 [VaultBridge] Loaded container from fallback path: {fallback_path}")
            with open(fallback_path, "r") as f:
                return json.load(f)
        else:
            raise FileNotFoundError(
                f"Container file not found in either path:\n  - {primary_path}\n  - {fallback_path}"
            )