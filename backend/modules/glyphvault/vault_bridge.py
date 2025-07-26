# backend/modules/glyphvault/vault_bridge.py

import random
import time
from typing import List, Dict, Any

# Simulated secure glyph vault entries (can be replaced with real Vault memory later)
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
    # Add delay to simulate real-time stream
    time.sleep(0.1)
    return get_mocked_vault_glyphs()