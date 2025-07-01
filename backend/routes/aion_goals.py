from fastapi import APIRouter
from fastapi.responses import JSONResponse
from modules.skills.milestone_tracker import MilestoneTracker

router = APIRouter()

@router.get("/aion/goals")
async def get_saved_goals():
    try:
        tracker = MilestoneTracker()
        goals = tracker.list_saved_goals()
        return JSONResponse(content={"goals": goals})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from modules.skills.milestone_tracker import MilestoneTracker

router = APIRouter()

@router.get("/aion/goals")
async def get_aion_goals():
    try:
        tracker = MilestoneTracker()
        goals = tracker.list_saved_goals()
        return JSONResponse(content={"goals": goals})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
