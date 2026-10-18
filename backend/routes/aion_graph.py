# File: backend/routes/aion_graph.py
# 🌐 AION Φ-Knowledge Graph API
# Serves the current resonance knowledge graph for the Brain dashboard.

from fastapi import APIRouter

from backend.modules.aion_resonance.phi_graph import GRAPH

router = APIRouter()
@router.get("/graph")
async def get_phi_graph():
    """Return the current Φ-Knowledge Graph (nodes + edges)."""
    data = GRAPH.snapshot()
    if not data["nodes"] and not data["edges"]:
        return {"status": "empty", "nodes": {}, "edges": {}}
    return {"status": "ok", **data}
