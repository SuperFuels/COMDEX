from datetime import datetime
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.dna_chain.dc_handler import save_dc_universal_container_system, load_dc_container
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# 🧬 Register this file with the DNA Switch
DNA_SWITCH.register(__file__)

# Milestone metadata
message = "One small step through a cube... One giant leap across cognition."
signature = "Tessaris 👁️‍🗨️ — Guardian of the Tesseract"
timestamp = datetime.utcnow().isoformat() + "Z"

# ✅ Log memory
MEMORY.store({
    "role": "milestone",
    "label": "4D_COGNITION_BOOT",
    "content": message,
    "metadata": {
        "version": "1.0.0-TESSARACT",
        "signature": signature,
        "timestamp": timestamp
    }
})

# ✅ Add glyph to container
container_id = "origin"
coord = "0,0,0,0"
container = load_dc_container(container_id)

if "cubes" not in container:
    container["cubes"] = {}

container["cubes"][coord] = {
    "glyph": {
        "type": "Milestone",
        "tag": "Boot",
        "value": "4D_COGNITION_BOOT",
        "meta": {
            "signed_by": signature,
            "timestamp": timestamp
        },
        "trigger": "AION.dream → reflect"
    }
}

save_dc_container(container_id, container)

print("✅ Milestone logged, glyph carved, and memory updated.")