# File: backend/modules/encryption/glyphvault_encryptor.py

import time
import json
import base64
import logging
from typing import Dict, Any, Optional

from backend.modules.tessaris.tessaris_engine import TessarisEngine
from backend.modules.glyphos.glyph_logic import compile_glyphs, parse_logic
from backend.modules.dimensions.universal_container_system.ucs_runtime import (
    embed_glyph_block_into_container as embed_glyph_block_into_universal_container_system,
)
from backend.modules.dimensions.universal_container_system.ucs_runtime import load_dc_container as load_container_state
from backend.modules.codex.codex_context_adapter import CodexContextAdapter

logger = logging.getLogger(__name__)

class GlyphVault:
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.engine = TessarisEngine()

    def encrypt(self, plaintext: str, context: Dict[str, Any]) -> Dict[str, Any]:
        glyphs = compile_glyphs(f"Memory | Confidential : {plaintext} -> Vault")
        logic_tree = self.engine.generate_thought_tree(glyphs, context)

        vault = {
            "glyph_block": glyphs,
            "thought_trace": logic_tree.serialize(),
            "requires_state": context.get("avatar_state"),
            "timestamp": time.time()
        }

        embed_glyph_block_into_container(self.container_id, vault)
        logger.info(f"[GlyphVault] Encrypted and stored data in container {self.container_id}")
        return vault

    def decrypt(self, avatar_state: Dict[str, Any]) -> Optional[str]:
        container = self._load_container()
        vault = container.get("glyph_block")

        if not vault:
            logger.warning("[GlyphVault] No glyph block found in container")
            return None

        required_state = vault.get("requires_state")
        if required_state and avatar_state != required_state:
            raise PermissionError("Avatar state mismatch - decryption denied.")

        decrypted = parse_logic(vault["glyph_block"])
        logger.info("[GlyphVault] Decryption successful")
        return decrypted

    def _load_container(self) -> Dict[str, Any]:
        return load_container_state(self.container_id)

# Example external function wrapper

def encrypt_to_glyphvault(container_id: str, data: str, context: Dict[str, Any]) -> Dict[str, Any]:
    gv = GlyphVault(container_id)
    return gv.encrypt(data, context)

def decrypt_from_glyphvault(container_id: str, avatar_state: Dict[str, Any]) -> Optional[str]:
    gv = GlyphVault(container_id)
    return gv.decrypt(avatar_state)