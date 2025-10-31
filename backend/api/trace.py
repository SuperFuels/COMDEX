# backend/api/trace.py
from fastapi import APIRouter
from backend.replay.reducer import ReplayReducer

router = APIRouter(prefix="/api/trace", tags=["Trace"])

@router.get("/recent")
def get_recent_traces():
    """
    Return recent cognition events buffered by ReplayReducer.
    Replaces legacy poll_trace() model.
    """
    try:
        return {"events": ReplayReducer.tail(200)}
    except Exception as e:
        return {"error": str(e), "events": []}