# backend/api/aion/export_scroll.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from tempfile import NamedTemporaryFile
from typing import List
import json
import uuid

from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.codex.codexlang_translator import parse_codexlang_string

router = APIRouter()

@router.post("/api/export_scroll/")
async def export_scroll(request: Request):
    try:
        payload = await request.json()
        label = payload.get("label")

        if not label:
            raise HTTPException(status_code=400, detail="Label is required")

        memory_entries = MEMORY.get(label)
        if not memory_entries:
            raise HTTPException(status_code=404, detail=f"No memory found for label '{label}'")

        # Build scroll data
        scroll = {
            "scroll_id": str(uuid.uuid4()),
            "label": label,
            "exported_at": request.headers.get("X-Timestamp") or request.headers.get("Date"),
            "entries": []
        }

        for entry in memory_entries:
            content = entry.get("content", "")
            try:
                logic_tree = parse_codexlang_string(content)
            except Exception as e:
                logic_tree = {"error": f"Parse failed: {str(e)}"}

            scroll["entries"].append({
                "timestamp": entry.get("timestamp"),
                "raw": content,
                "logic_tree": logic_tree
            })

        # Write to temp file with .codexscroll extension
        with NamedTemporaryFile(delete=False, suffix=".codexscroll", mode="w") as tmp:
            json.dump(scroll, tmp, indent=2)
            tmp_path = tmp.name

        return FileResponse(
            path=tmp_path,
            filename=f"scroll_{label}.codexscroll",
            media_type="application/json"
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})