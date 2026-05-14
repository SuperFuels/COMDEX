# File: backend/routes/aion_graph.py
# 🌐 AION Φ-Knowledge Graph API
# Serves the current resonance knowledge graph for the Brain dashboard.

from fastapi import APIRouter
import os, json

router = APIRouter()
GRAPH_PATH = "data/phi_graph.json"

@router.get("/graph")
async def get_phi_graph():
    """Return the current Φ-Knowledge Graph (nodes + edges)."""
    if not os.path.exists(GRAPH_PATH):
        return {"status": "empty", "nodes": {}, "edges": {}}
    with open(GRAPH_PATH, "r") as f:
        data = json.load(f)
    return {"status": "ok", **data}