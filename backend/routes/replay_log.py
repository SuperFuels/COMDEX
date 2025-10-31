from fastapi import APIRouter, Query
from backend.replay.reducer import ReplayReducer

router = APIRouter(prefix="/api/replay", tags=["Replay"])

@router.get("/log")
def get_replay_log(docId: str = Query("default")):
    try:
        frames = ReplayReducer.dump(docId)
        return {"docId": docId, "frames": frames}
    except Exception as e:
        return {"error": str(e), "frames": []}