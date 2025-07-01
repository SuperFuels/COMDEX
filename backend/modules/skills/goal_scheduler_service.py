from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from modules.skills.goal_scheduler_loop import GoalSchedulerLoop

app = FastAPI()
scheduler = GoalSchedulerLoop()

@app.post("/run-goals")
async def run_goals():
    try:
        await scheduler.run_once()
        return JSONResponse(content={"status": "success", "message": "Goals run completed"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
