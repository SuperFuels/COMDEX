from fastapi import APIRouter
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dna_chain.container_linker import ContainerLinker

router = APIRouter()

@router.post("/ucs/teleport")
def teleport_between_links(source_id: str, direction: str):
    """
    UCS-native teleport API. Uses ContainerLinker to resolve chained links.
    """
    linker = ContainerLinker(ucs_runtime.containers)
    target_id = linker.registry[source_id]["nav"].get(direction)

    if not target_id:
        return {"status": "error", "message": f"No linked container in direction: {direction}"}

    # TODO: Invoke teleport orchestration + GlyphPush if required
    print(f"🛰 Teleporting {source_id} → {target_id} via {direction}")
    return {"status": "ok", "source": source_id, "target": target_id}