# backend/utils/bundle_builder.py

import json
import base64
import hashlib
from datetime import datetime
from backend.modules.consciousness.state_manager import StateManager
from backend.modules.avatar.avatar_core import get_avatar_state
from backend.modules.glyphos.microgrid_index import MicrogridIndex
from backend.modules.dna_chain.dc_handler import load_dimension_by_file

def bundle_container(container_id: str) -> dict:
    state = StateManager()
    container_path = state.get_container_path_by_id(container_id)

    if not container_path:
        raise ValueError(f"❌ Container not found: {container_id}")

    # Load glyphs
    dimension = load_dimension_by_file(container_path)
    microgrid = dimension.get("microgrid", {})
    index = MicrogridIndex()
    index.import_index(microgrid)

    # Avatar state
    avatar = get_avatar_state(container_id)

    # Metadata
    bundle = {
        "container_id": container_id,
        "timestamp": datetime.utcnow().isoformat(),
        "avatar": avatar,
        "glyphs": index.glyph_map,
        "metadata": {
            "origin": container_path,
            "hash": hashlib.sha256(json.dumps(microgrid).encode()).hexdigest(),
        },
    }

    encoded = base64.b64encode(json.dumps(bundle).encode()).decode()
    return {
        "status": "success",
        "bundle": encoded,
        "preview": bundle["metadata"]
    }