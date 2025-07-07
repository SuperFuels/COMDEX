from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from backend.modules.skills.goal_scheduler_loop import GoalSchedulerLoop

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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
