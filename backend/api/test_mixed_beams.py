# ✅ File: backend/api/test_mixed_beams.py

from fastapi import APIRouter
from backend.modules.visualization.beam_payload_builder import build_test_beam_payload

router = APIRouter()

@router.get("/api/test-mixed-beams")
async def test_mixed_beams():
    """
    Returns a hybrid symbolic beam + glyph data payload for QFC testing.
    Includes entangled links, predicted nodes, SQI scoring, collapse states, and QWave metadata.
    """
    try:
        beam_data = build_test_beam_payload()
        return beam_data
    except Exception as e:
        return {"error": str(e), "status": "failed"}