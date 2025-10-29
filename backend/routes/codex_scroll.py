# 📁 backend/routes/codex_scroll.py

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Core imports
from backend.modules.codex.codex_emulator import CodexEmulator
from backend.modules.hexcore.memory_engine import MEMORY

# Photon and Photon Page integration
from backend.modules.photon.photon_executor import execute_photon_capsule, parse_photon_file
from backend.modules.ptn.ptn_runner import run_photon_page

router = APIRouter()
emulator = CodexEmulator()


# ─────────────────────────────────────────────────────────────
# 🧠  Codex Scroll Execution
# ─────────────────────────────────────────────────────────────

class ScrollRequest(BaseModel):
    scroll: str
    context: Optional[Dict[str, Any]] = {}


@router.post("/codex/scroll")
async def run_scroll(request: ScrollRequest):
    """
    Execute a CodexLang scroll via CodexEmulator.
    """
    try:
        result = emulator.run(request.scroll, request.context)

        MEMORY.store({
            "label": "codex_scroll_execution",
            "type": "scroll",
            "scroll": request.scroll,
            "context": request.context,
            "result": result
        })

        return {"status": "ok", "scroll": request.scroll, "result": result}

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────────────────────
# 💡 Photon Capsule Execution (.phn)
# ─────────────────────────────────────────────────────────────

@router.post("/codex/run-photon")
async def run_photon(body: dict):
    """
    Execute a Photon (.phn) capsule file or inline content.
    """
    try:
        content = body.get("content")
        path = body.get("path")

        if content:
            # Parse inline .phn content
            tmp_path = Path("/tmp/inline_capsule.phn")
            tmp_path.write_text(content, encoding="utf-8")
            capsules = parse_photon_file(tmp_path)
        elif path:
            capsules = parse_photon_file(Path(path))
        else:
            return {"status": "error", "error": "Must provide 'content' or 'path'."}

        results = [execute_photon_capsule(c) for c in capsules]
        return {"status": "ok", "capsules": [c.name for c in capsules], "results": results}

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─────────────────────────────────────────────────────────────
# 📘 Photon Page Execution (.ptn)
# ─────────────────────────────────────────────────────────────

@router.post("/codex/run-ptn")
async def run_ptn(body: dict):
    """
    Execute a Photon Page (.ptn) capsule sent via API.
    Accepts either:
      • path → to .ptn file
      • content → dict representing PhotonPage JSON
    """
    try:
        if "content" in body:
            tmp_path = Path("/tmp/api_photon_page.ptn")
            tmp_path.write_text(json.dumps(body["content"], indent=2), encoding="utf-8")
            result = run_photon_page(str(tmp_path))
        elif "path" in body:
            result = run_photon_page(body["path"])
        else:
            return {"status": "error", "error": "Must provide 'content' or 'path'."}

        MEMORY.store({
            "label": "photon_page_execution",
            "type": "ptn",
            "source": body.get("path") or "inline",
            "result": result
        })

        return result

    except Exception as e:
        return {"status": "error", "error": str(e)}