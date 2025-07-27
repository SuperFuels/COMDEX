# File: backend/api/aion/plugins.py

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.modules.knowledge_graph.indexes.plugin_index import get_loaded_plugins

router = APIRouter()

@router.get("/api/aion/plugins")
def list_plugins():
    return JSONResponse(content={"plugins": get_loaded_plugins()})