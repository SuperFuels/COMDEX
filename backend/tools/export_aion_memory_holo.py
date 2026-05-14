# export_aion_memory_holo.py
# ================================================================
# 📤 export_aion_memory_holo.py - export AION memory field to .holo
# ================================================================
import logging

from backend.modules.aion_cognition.aion_memory_holo_api import write_holo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    holo = write_holo()
    storage = holo.get("metadata", {}).get("storage", {})
    path = storage.get("path", "?")
    print(f"✅ Exported AION memory holo -> {path}")