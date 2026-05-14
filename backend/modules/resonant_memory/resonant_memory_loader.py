# ============================================================
# 🧬 Resonant Memory Loader
# ============================================================
# Provides a unified interface to load scrolls or memory entries
# from Photon Memory or Resonant Memory caches for the SCI system.

from __future__ import annotations
from typing import Dict, Any
import json
import os

try:
    from backend.modules.photon_memory.photon_memory_entry import load_photon_memory_entry
except Exception:
    def load_photon_memory_entry(scroll_id: str) -> Dict[str, Any]:
        print(f"[StubPhotonMemory] No photon_memory_entry backend found.")
        return {"id": scroll_id, "data": f"stub::{scroll_id}", "meta": {"stub": True}}

try:
    from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
    RMC = ResonantMemoryCache()
except Exception:
    class _StubRMC:
        def load(self, key): 
            print(f"[StubRMC] No cache found for {key}")
            return None
    RMC = _StubRMC()

# ============================================================
# 🔹 API
# ============================================================

def load_scroll_from_memory(scroll_id: str) -> Dict[str, Any]:
    """
    Loads a symbolic scroll from memory.
    Prefers Resonant Memory cache; falls back to Photon Memory.
    """
    # 1️⃣ Try Resonant Memory Cache
    cache = RMC.load(scroll_id)
    if cache:
        print(f"[RMC] Loaded scroll '{scroll_id}' from resonant cache.")
        return cache

    # 2️⃣ Try Photon Memory Entry
    entry = load_photon_memory_entry(scroll_id)
    if entry:
        print(f"[PhotonMemory] Loaded scroll '{scroll_id}' via Photon Memory Entry.")
        return entry

    # 3️⃣ Fallback Stub
    print(f"[FallbackMemory] Created synthetic scroll for '{scroll_id}'.")
    return {
        "id": scroll_id,
        "content": f"synthetic::{scroll_id}",
        "metadata": {"source": "fallback", "exists": False},
    }