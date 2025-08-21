# File: backend/api/symbol_tree.py

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from backend.modules.symbolic.symbol_tree_generator import build_tree_from_container
from backend.modules.dimensions.containers.container_loader import load_decrypted_container as load_container_by_id
import gzip
import json

router = APIRouter()

@router.get("/symbol_tree/{container_id}")
async def get_symbol_tree(
    container_id: str,
    compress: bool = Query(False, description="Compress the output using Gzip")
):
    try:
        # Ensure the container exists
        container = load_container_by_id(container_id)
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")

        # Build symbolic tree
        tree = build_tree_from_container(container)

        tree_dict = tree.to_dict()
        data = json.dumps(tree_dict, indent=2)

        if compress:
            compressed = gzip.compress(data.encode())
            return Response(content=compressed, media_type="application/gzip")

        return JSONResponse(content=tree_dict)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))