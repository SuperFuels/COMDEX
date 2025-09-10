import asyncio
from typing import Optional
from backend.modules.dimensions.containers.container_loader import load_container_by_id
from backend.modules.visualization.qfc_payload_utils import to_qfc_payload
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update

def sync_container_to_qfc(container_id: str, limit: Optional[int] = None) -> None:
    """
    Broadcast all glyphs and QWave beams from the container to the QFC WebSocket.
    Useful for initializing the QFC view from a .dc.json container.

    Args:
        container_id: The ID of the container to sync.
        limit: Optional limit on number of glyphs to broadcast.
    """
    container = load_container_by_id(container_id)
    if not container:
        print(f"[QFC Sync] ❌ Container '{container_id}' not found.")
        return

    # Sync glyphs (nodes)
    glyphs = container.get("glyph_grid", [])
    if limit:
        glyphs = glyphs[-limit:]

    for glyph in glyphs:
        context = {
            "container_id": container_id,
            "source_node": glyph.get("metadata", {}).get("node_id", "origin")
        }
        qfc_payload = to_qfc_payload(glyph, context)
        asyncio.create_task(broadcast_qfc_update(container_id, qfc_payload))

    # Sync QWave beams if present
    qwave_beams = container.get("symbolic", {}).get("qwave_beams", [])
    for beam in qwave_beams:
        beam_payload = {
            "glyph": "beam",
            "op": "inject",
            "metadata": beam
        }
        context = {
            "container_id": container_id,
            "source_node": beam.get("source_id", "origin")
        }
        qfc_payload = to_qfc_payload(beam_payload, context)
        asyncio.create_task(broadcast_qfc_update(container_id, qfc_payload))

    print(f"[QFC Sync] ✅ Synced {len(glyphs)} glyphs and {len(qwave_beams)} beams for container '{container_id}'")