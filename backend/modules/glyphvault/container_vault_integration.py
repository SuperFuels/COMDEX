from typing import Optional

from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.glyphvault.key_manager import key_manager
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime  # ✅ UCS Runtime sync
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator  # ✅ Safe SoulLaw accessor

_vault_seen = set()

def lazy_broadcast_event(payload):
    """Lazy-imports broadcast_event to avoid circular import."""
    from backend.routes.ws.glyphnet_ws import broadcast_event
    from asyncio import create_task
    create_task(broadcast_event(payload))

def get_state():
    from backend.modules.consciousness.state_manager import STATE
    return STATE

# Load encryption key securely from key manager singleton
ENCRYPTION_KEY = key_manager.key
vault_manager: Optional[ContainerVaultManager] = None

def get_vault_manager():
    global vault_manager
    if vault_manager is None:
        from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
        from backend.settings.encryption_config import ENCRYPTION_KEY  # or wherever it's defined
        vault_manager = ContainerVaultManager(ENCRYPTION_KEY)
    return vault_manager

def decrypt_glyph_vault(container_data: dict, avatar_state: dict = None) -> dict:
    """
    Decrypt glyph vault, load glyph metadata into container cubes, 
    sync UCS runtime, enforce SoulLaw, and broadcast GHX visualization.
    """
    encrypted_blob = container_data.get("glyph_vault")
    if not encrypted_blob:
        return container_data

    if isinstance(encrypted_blob, str):
        encrypted_blob = bytes.fromhex(encrypted_blob)

    # ✅ SoulLaw: Validate container before decryption
    soul_law = get_soul_law_validator()
    cid = container_data.get("id") or container_data.get("name")
    if cid not in _vault_seen:
        try:
            soul_law.validate_container(container_data)
            _vault_seen.add(cid)
        except Exception as e:
            print(f"❌ SoulLaw: Container decryption blocked – {e}")
            return container_data

    # ✅ Avatar validation before decrypt
    if not soul_law.validate_avatar(avatar_state):
        raise PermissionError("[🔒] Vault integration blocked by SoulLaw")

    success = vault_manager.load_container_glyph_data(encrypted_blob, avatar_state=avatar_state)
    if not success:
        print("[Vault] Failed to decrypt glyph vault.")
        return container_data

    # Merge glyph metadata into container cubes
    glyph_map = vault_manager.get_microgrid().glyph_map
    cubes = container_data.setdefault("cubes", {})
    for coord_tuple, meta in glyph_map.items():
        x, y, z, layer = coord_tuple
        key = f"{x},{y},{z}" if layer is None else f"{x},{y},{z},{layer}"
        cubes[key] = meta

    print(f"[Vault] Loaded {len(glyph_map)} glyphs from glyph vault.")

    # ✅ UCS Runtime Sync
    ucs = get_ucs_runtime()
    ucs.save_container(container_data["id"], container_data)

    # ✅ GHX Visualization Sync (lazy import to avoid circular import)
    lazy_broadcast_event({
        "type": "vault_decrypt",
        "container_id": container_data.get("id"),
        "glyph_count": len(glyph_map),
        "tags": ["🔓", "GHX"]
    })

    return container_data


def encrypt_and_embed_glyph_vault(container_data: dict) -> dict:
    """
    Extract glyph metadata, encrypt it, and embed into container vault. 
    Enforce SoulLaw, sync UCS runtime, and emit SQI events.
    """
    cubes = container_data.get("cubes", {})
    glyph_data = {}

    for coord_str, cube in cubes.items():
        glyph_meta = {
            k: v for k, v in cube.items()
            if k in ("glyph", "timestamp", "source", "metadata", "activations", "energy")
        }
        glyph_data[coord_str] = glyph_meta

    # ✅ SoulLaw Validation (Pre-encrypt)
    soul_law = get_soul_law_validator()
    try:
        soul_law.validate_container(container_data)
    except Exception as e:
        print(f"❌ SoulLaw: Vault encryption blocked – {e}")
        return container_data

    # Encrypt glyph metadata
    encrypted_blob = vault_manager.save_container_glyph_data(glyph_data)
    container_data["glyph_vault"] = encrypted_blob.hex()

    # Optionally clear plaintext glyph data
    for cube in cubes.values():
        cube.pop("glyph", None)
        cube.pop("source", None)
        cube.pop("metadata", None)

    print(f"[Vault] Encrypted and embedded {len(glyph_data)} glyphs into glyph vault.")

    # ✅ UCS Runtime Sync
    ucs = get_ucs_runtime()
    ucs.save_container(container_data["id"], container_data)

    # ✅ SQI Event Emission (lazy import to avoid circular import)
    lazy_broadcast_event({
        "type": "vault_encrypt",
        "container_id": container_data.get("id"),
        "glyph_count": len(glyph_data),
        "tags": ["🔒", "SQI"]
    })

    return container_data