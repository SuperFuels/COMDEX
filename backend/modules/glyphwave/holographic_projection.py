import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any

def generate_ghx_projection(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encode a container into a holographic GHX projection beam format.
    Simulates symbolic light-beam projection.
    """
    projection_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    # Generate a hash for symbolic integrity tracking
    raw = str(container.get("id", "")) + str(container.get("nodes", "")) + timestamp
    projection_hash = hashlib.sha256(raw.encode()).hexdigest()

    return {
        "projection_id": projection_id,
        "timestamp": timestamp,
        "projection_hash": projection_hash,
        "symbol_tree": container.get("nodes", []),
        "links": container.get("links", []),
        "metadata": {
            "container_id": container.get("id"),
            "projection_source": "glyphwave_beam",
            "qglyph_count": sum(1 for n in container.get("nodes", []) if "qglyph" in n),
        }
    }