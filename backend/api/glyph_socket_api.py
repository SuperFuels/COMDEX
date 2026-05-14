# backend/routes/api/glyph_socket_api.py

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.modules.glyphnet.glyph_socket import GlyphSocket

router = APIRouter()
glyph_socket = GlyphSocket()

@router.post("/glyph_socket/dispatch")
async def dispatch_teleport_packet(request: Request):
    try:
        payload = await request.json()
        result = glyph_socket.dispatch(payload)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"status": "❌ Failed", "error": str(e)},
            status_code=400
        )