import random
import time
import os
import json
from typing import List, Dict, Any

# ==============================
# 🔹 Simulated Vault Glyphs
# ==============================

VAULT_GLYPHS = [
    {
        "id": "v1",
        "glyph": "⧖",
        "position": [-1.5, 1.5, -2],
        "color": "#ffaa00",
        "memoryEcho": False,
        "fromVault": True
    },
    {
        "id": "v2",
        "glyph": "⌘",
        "position": [1.5, 1.5, -2],
        "color": "#00cc88",
        "memoryEcho": True,
        "fromVault": True
    },
    {
        "id": "v3",
        "glyph": "↔",
        "position": [0, 2.5, -1],
        "color": "#aa66ff",
        "memoryEcho": False,
        "fromVault": True,
        "entangled": ["v2"]
    },
    {
        "id": "v4",
        "glyph": "⬁",
        "position": [0, -2.5, -1],
        "color": "#ff4444",
        "memoryEcho": False,
        "fromVault": True,
        "entangled": ["v1"]
    }
]

def get_mocked_vault_glyphs() -> List[Dict[str, Any]]:
    """
    Returns a jittered list of glyphs from the simulated Vault.
    Used for holographic or GHX projection.
    """
    jittered = []
    for entry in VAULT_GLYPHS:
        dx, dy, dz = [random.uniform(-0.1, 0.1) for _ in range(3)]
        clone = entry.copy()
        clone["position"] = [
            round(clone["position"][0] + dx, 2),
            round(clone["position"][1] + dy, 2),
            round(clone["position"][2] + dz, 2)
        ]
        jittered.append(clone)
    return jittered

def stream_vault_glyphs(identity: str = "AION-000X") -> List[Dict[str, Any]]:
    """
    Streams glyphs for GHXVisualizer.tsx from Vault system.
    Accepts identity for future filtering or security logic.
    """
    time.sleep(0.1)
    return get_mocked_vault_glyphs()

def get_container_snapshot_id(container_id: str) -> str:
    """
    Retrieves a symbolic snapshot ID for a given container.
    Currently mocked; integrate with Vault for persistence.
    """
    return f"SNAP-{container_id}-{int(time.time())}"

# ==============================
# 🔐 Vault Loader Integration
# ==============================

from backend.modules.glyphvault.container_vault_manager import ContainerVaultManager
from backend.modules.glyphvault.key_manager import get_encryption_key
from backend.modules.consciousness.state_manager import state_manager  # ✅ Singleton instance

vault_manager = ContainerVaultManager(encryption_key=get_encryption_key())

def load_container_by_id(container_id: str) -> Dict[str, Any]:
    """
    Loads a container by ID or path, with validation, fallback, and state registration.
    """
    print(f"📦 [VaultBridge] Attempting to load container: {container_id}")
    container_data = None

    # 🔍 Case 1: Full path (file)
    if os.path.exists(container_id) and container_id.endswith(".dc.json"):
        print(f"📂 [VaultBridge] Detected full path - loading from path: {container_id}")
        container_data = vault_manager.load_container_from_path(container_id)

    # 🔍 Case 2: Treat as ID
    else:
        print(f"🆔 [VaultBridge] Treating as container ID: {container_id}")
        container_data = vault_manager.load_container_by_id(container_id)

        # 🛠️ Fallback: Try direct file load from containers folder
        if container_data is None:
            fallback_path = f"backend/modules/dimensions/containers/{container_id}.dc.json"
            print(f"📂 [VaultBridge] Fallback path: {fallback_path}")
            if os.path.exists(fallback_path):
                try:
                    with open(fallback_path, "r") as f:
                        container_data = json.load(f)
                except Exception as e:
                    print(f"❌ Failed to load container from file {fallback_path}: {e}")
            else:
                print(f"⚠️ Fallback container file not found: {fallback_path}")

    # 🚨 Fail-fast: No container loaded
    if container_data is None:
        raise RuntimeError(f"❌ Failed to load container '{container_id}': returned None.")

    # 🧪 Format validation
    if not isinstance(container_data, dict):
        raise TypeError(f"❌ Invalid container format for '{container_id}': expected dict, got {type(container_data)}")

    # 🔗 Register to global state
    state_manager.set_current_container(container_data)
    container_id = container_data.get("id", "unknown")
    print(f"✅ [VaultBridge] Container registered to state_manager: {container_id}")
    print(f"📦 [VaultBridge] Container keys: {list(container_data.keys())}")

    return container_data
