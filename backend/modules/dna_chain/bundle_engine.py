# File: backend/modules/dna_chain/bundle_engine.py

import base64
import json
from datetime import datetime
from modules.consciousness.state_manager import get_container_state
from modules.dna_chain.glyph_grid import get_active_glyphs

def create_bundle(container_id: str):
    state = get_container_state(container_id)
    glyphs = get_active_glyphs(container_id)

    bundle = {
        "container_id": container_id,
        "timestamp": datetime.utcnow().isoformat(),
        "state": state,
        "glyphs": glyphs,
    }

    encoded = base64.b64encode(json.dumps(bundle).encode()).decode()
    return {
        "bundle_data": encoded,
        "meta": {
            "container_id": container_id,
            "size": len(encoded),
        }
    }