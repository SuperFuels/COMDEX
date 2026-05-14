# backend/routes/codex_scroll_routes.py

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from modules.codex.codex_scroll_library import save_named_scroll, list_scrolls
import json
from pathlib import Path

router = APIRouter()

class ScrollSaveRequest(BaseModel):
    name: str
    tree: dict

@router.post("/codex/save")
def save_scroll(req: ScrollSaveRequest):
    save_named_scroll(req.name, req.tree)
    return {"status": "ok"}

@router.get("/codex/list")
def list_saved_scrolls():
    return {"scrolls": list_scrolls()}

@router.get("/codex/download/{name}")
def download_scroll(name: str):
    path = Path(f"data/codex_scrolls/{name}.codex")
    if not path.exists():
        return {"error": "Not found"}
    return FileResponse(path, filename=f"{name}.codex", media_type="application/json")