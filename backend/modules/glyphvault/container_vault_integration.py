# backend/modules/glyphvault/container_vault_integration.py

from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.glyphvault.key_manager import key_manager

def get_state():
    from backend.modules.consciousness.state_manager import STATE
    return STATE

# Load encryption key securely from key manager singleton
ENCRYPTION_KEY = key_manager.key

vault_manager = ContainerVaultManager(ENCRYPTION_KEY)

def decrypt_glyph_vault(container_data: dict, avatar_state: dict = None) -> dict:
    """
    If container_data contains encrypted glyph vault, decrypt and load glyph metadata.
    Merge glyph metadata into container 'cubes' or other relevant fields.
    """
    encrypted_blob = container_data.get("glyph_vault")
    if not encrypted_blob:
        # No glyph vault, return as is
        return container_data

    if isinstance(encrypted_blob, str):
        encrypted_blob = bytes.fromhex(encrypted_blob)

    success = vault_manager.load_container_glyph_data(encrypted_blob, avatar_state=avatar_state)
    if not success:
        # Decryption failed - log and proceed without glyph vault
        print("[Vault] Failed to decrypt glyph vault.")
        return container_data

    # Merge glyph metadata from vault into container cubes
    glyph_map = vault_manager.get_microgrid().glyph_map
    cubes = container_data.setdefault("cubes", {})
    for coord_tuple, meta in glyph_map.items():
        x, y, z, layer = coord_tuple
        key = f"{x},{y},{z}" if layer is None else f"{x},{y},{z},{layer}"
        cubes[key] = meta

    print(f"[Vault] Loaded {len(glyph_map)} glyphs from glyph vault.")
    return container_data

def encrypt_and_embed_glyph_vault(container_data: dict) -> dict:
    """
    Extract glyph metadata from container cubes, encrypt it, and embed as 'glyph_vault' field.
    Optionally remove plaintext glyph data from cubes to secure container data.
    """
    cubes = container_data.get("cubes", {})
    glyph_data = {}

    for coord_str, cube in cubes.items():
        glyph_meta = {
            k: v for k, v in cube.items()
            if k in ("glyph", "timestamp", "source", "metadata", "activations", "energy")
        }
        glyph_data[coord_str] = glyph_meta

    # Encrypt glyph metadata
    encrypted_blob = vault_manager.save_container_glyph_data(glyph_data)

    # Store hex-encoded encrypted blob
    container_data["glyph_vault"] = encrypted_blob.hex()

    # Optionally clear plaintext glyph cubes for security
    for cube in cubes.values():
        cube.pop("glyph", None)
        cube.pop("source", None)
        cube.pop("metadata", None)

    print(f"[Vault] Encrypted and embedded {len(glyph_data)} glyphs into glyph vault.")
    return container_data