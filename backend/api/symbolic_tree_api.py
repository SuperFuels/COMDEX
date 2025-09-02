# File: backend/api/symbolic_tree_api.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from pydantic import BaseModel
import os

# Core Tree Logic
from backend.modules.symbolic.symbol_tree_generator import (
    build_symbolic_tree_from_container,
    inject_mutation_path,
    score_path_with_SQI,
)

from backend.modules.codex.symbolic_registry import symbolic_registry
from backend.modules.dimensions.containers.container_loader import load_container_from_file

router = APIRouter()

class TreeResponse(BaseModel):
    success: bool
    tree: dict
    message: str

@router.get("/api/symbolic/tree", response_model=TreeResponse)
def get_symbolic_tree(
    container_id: str = Query(..., description="Container ID or .dc.json path"),
    mode: str = Query("json", description="Output mode: ascii or json"),
    inject_glyph: Optional[str] = Query(None, description="Inject glyph ID or name"),
    inject_from: Optional[str] = Query(None, description="Node ID to inject from"),
    score: bool = Query(False, description="Apply SQI scoring"),
):
    try:
        # 📦 Load container
        if os.path.exists(container_id) and container_id.endswith(".dc.json"):
            container = load_container_from_file(container_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid container ID or path")

        # 🌳 Build tree
        tree = build_symbolic_tree_from_container(container)

        # 🔁 Inject mutation if requested
        if inject_glyph:
            glyph_obj = symbolic_registry.get(inject_glyph)
            if not glyph_obj:
                raise HTTPException(status_code=400, detail=f"Unknown glyph '{inject_glyph}'")
            inject_from_node = inject_from or tree.root.id
            inject_mutation_path(tree, inject_from_node, glyph_obj)

        # 🔬 SQI Scoring
        if score:
            score_path_with_SQI(tree)

        return TreeResponse(
            success=True,
            tree=tree.to_dict() if mode == "json" else {},
            message=f"Tree built with {len(tree.node_index)} nodes"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))