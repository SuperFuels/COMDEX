# 📁 backend/routes/codex_mutate_scroll.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

from backend.modules.codex.scroll_mutation_engine import mutate_scroll_tree
from backend.modules.hexcore.memory_engine import MEMORY

router = APIRouter()

class ScrollTreeRequest(BaseModel):
    tree: List[Dict[str, Any]]

@router.post("/codex/mutate")
async def mutate_scroll(req: ScrollTreeRequest):
    try:
        mutated = mutate_scroll_tree(req.tree)
        MEMORY.store({
            "label": "scroll_mutation",
            "original": req.tree,
            "mutated": mutated
        })
        return {"status": "ok", "mutated": mutated}
    except Exception as e:
        return {"status": "error", "error": str(e)}