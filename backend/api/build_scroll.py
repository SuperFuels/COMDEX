# 📁 backend/routes/api/build_scroll.py

from fastapi import APIRouter, Request
from backend.modules.consciousness.state_manager import STATE
from backend.modules.codex.codex_formatter import format_codex_scroll

router = APIRouter()

@router.get("/build_scroll")
async def build_codex_scroll(request: Request):
    container = STATE.get_current_container()
    if not container:
        return {"status": "error", "message": "No container loaded"}

    logic_tree = container.get("symbolic_logic", [])
    scroll_lines = []

    for node in logic_tree:
        symbol = node.get("symbol", "")
        name = node.get("name", "unknown")
        logic = node.get("logic", "")
        args = node.get("args", [])

        if symbol == "⟦ Theorem ⟧":
            # 📘 Format Lean theorem
            proof = next((a["value"] for a in args if a.get("type") == "Proof"), "unknown")
            scroll_lines.append(f"📘 Theorem {name}: {logic}")
            scroll_lines.append(f"🧠 Proof: {proof}")
        else:
            # 🧠 Default formatting for other glyphs
            scroll_lines.append(f"{symbol} {name}: {logic}")

    return {
        "status": "ok",
        "container_id": container.get("id"),
        "scroll": scroll_lines
    }