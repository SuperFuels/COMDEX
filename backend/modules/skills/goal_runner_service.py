from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.modules.skills.goal_runner import GoalRunner

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

app = FastAPI(title="AION Goal Runner Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for security as needed
    allow_methods=["POST"],
    allow_headers=["*"],
)

runner = GoalRunner()

@app.post("/run-goals")
async def run_goals():
    active_goals = runner.engine.get_active_goals()
    if not active_goals:
        return {"message": "No active goals to complete."}

    results = []
    for goal in active_goals:
        try:
            runner.complete_goal(goal["name"])
            results.append({"goal": goal["name"], "status": "completed"})
        except Exception as e:
            results.append({"goal": goal["name"], "status": "failed", "error": str(e)})
    return {"results": results}
