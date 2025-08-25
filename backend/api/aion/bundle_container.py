# File: backend/api/aion/bundle_container.py

from fastapi import APIRouter
from backend.utils.bundle_builder import bundle_universal_container_system  # ✅ Corrected import
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime  # ✅ UCS integration
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer  # ✅ KG logging (updated)
from backend.routes.ws.glyphnet_ws import broadcast_event  # ✅ GHX/SQI sync

router = APIRouter()

@router.get("/api/aion/bundle/{container_id}")
async def bundle(container_id: str):
    kg_writer = get_kg_writer()

    try:
        # ✅ UCS Runtime: Ensure container is loaded & saved before bundling
        ucs = get_ucs_runtime()
        container = ucs.load_container(container_id)

        # ✅ Bundle container with UCS-aware builder
        result = bundle_universal_container_system(container_id)

        # ✅ Knowledge Graph Logging
        kg_writer.inject_glyph(
            content=f"Bundled container {container_id}",
            glyph_type="bundle_event",
            metadata={"container_id": container_id, "tags": ["bundle", "UCS"]},
            plugin="BundleAPI"
        )

        # ✅ GHX/SQI Visualization Event
        broadcast_event({
            "type": "bundle_complete",
            "container_id": container_id,
            "tags": ["📦", "GHX"]
        })

        return {
            "status": "success",
            "container_id": container_id,
            "bundle": result
        }

    except Exception as e:
        # ✅ Error case logging to KG
        kg_writer.inject_glyph(
            content=f"Bundle failed for container {container_id}: {e}",
            glyph_type="error",
            metadata={"container_id": container_id, "tags": ["bundle", "error"]},
            plugin="BundleAPI"
        )

        return {
            "status": "error",
            "container_id": container_id,
            "error": str(e)
        }