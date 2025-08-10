# backend/modules/encryption/glyph_vault.py
"""
Back-compat adapter: expose GlyphVault at the expected module path.
"""

# Reuse your existing implementation
from .glyphvault_encryptor import GlyphVault as _GlyphVault

# Optional: thin alias so external code can `from ...glyph_vault import GlyphVault`
class GlyphVault(_GlyphVault):
    pass

# (Optional helpers to preserve old function names if any caller used them)
def encrypt_to_glyphvault(container_id: str, data: str, context: dict):
    return GlyphVault(container_id).encrypt(data, context)

def decrypt_from_glyphvault(container_id: str, avatar_state: dict):
    return GlyphVault(container_id).decrypt(avatar_state)