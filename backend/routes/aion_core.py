from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import traceback

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.memory_reflector import MemoryReflector
from backend.modules.hexcore.ai_wallet import AIWallet
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.aion_reflection.reflection_engine import ReflectionEngine
from backend.modules.skills.boot_archiver import archive_learned_skills

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

# ------------------------------
# Request Models
# ------------------------------

class SeedRequest(BaseModel):
    seed: str = "AION should explore swarm intelligence for decentralized agent coordination."

# ------------------------------
# API Endpoints
# ------------------------------

@router.post("/run-learning-cycle")
async def run_learning_cycle(seed_req: SeedRequest):
    try:
        memory = MemoryEngine()
        reflector = MemoryReflector()
        wallet = AIWallet()
        planner = StrategyPlanner()
        tracker = MilestoneTracker()
        goal_engine = GoalEngine()
        boot_selector = BootSelector()
        reflection_engine = ReflectionEngine()

        # Seed
        label = memory.store({"label": "api_seed", "content": seed_req.seed.strip()})

        # Reflect
        reflector.reflect()

        # Reward tokens
        wallet.earn("STK", 10)

        # Generate strategies → milestones → goals
        planner.generate_with_ids()
        for strat in planner.strategies:
            milestone_name = f"milestone_for_{strat['id'][:8]}"
            tracker.add_milestone(
                name=milestone_name,
                excerpt=strat.get("goal", ""),
                source="api"
            )
            goal_engine.create_goal_from_milestone(
                milestone_name,
                description=f"Goal linked to strategy: {strat.get('goal', '')}",
                reward=5,
                priority=5,
                origin_strategy_id=strat['id']
            )

        # Boot skill match
        latest_memory = memory.get_all()[-1].get("content", "")
        skill = boot_selector.find_matching_skill(latest_memory)

        # Reflect again via ReflectionEngine
        summary = reflection_engine.run(limit=5)

        archive_learned_skills()

        return {
            "status": "complete",
            "seeded_label": label,
            "boot_skill_match": skill,
            "strategy_count": len(planner.strategies),
            "reflection_summary": summary
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AION cycle error: {str(e)}")

@router.post("/boot-skill")
async def boot_skill():
    memory = MemoryEngine()
    boot_selector = BootSelector()
    memories = memory.get_all()
    if not memories:
        raise HTTPException(status_code=404, detail="No memory available")
    latest = memories[-1].get("content", "")
    match = boot_selector.find_matching_skill(latest)
    return {"boot_skill_match": match}

@router.post("/run-dream")
async def run_dream():
    engine = ReflectionEngine()
    try:
        summary = engine.run(limit=5)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reflection error: {str(e)}")

@router.post("/skill-reflect")
async def skill_reflect():
    try:
        reflector = MemoryReflector()
        reflector.reflect()
        return {"status": "reflection complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill reflection error: {str(e)}")

@router.get("/goal")
async def get_goals():
    engine = GoalEngine()
    return {"goals": engine.get_goals()}

@router.get("/status")
async def get_status():
    wallet = AIWallet()
    memory = MemoryEngine()
    return {
        "wallet": wallet.get_all_balances(),
        "memory_count": len(memory.get_all())
    }

# ------------------------------
# 🔁 Catch-All Command Dispatcher
# ------------------------------

@router.post("/command")
async def command_handler(payload: dict):
    command = payload.get("command", "").strip()

    if command == "run-dream":
        return await run_dream()

    elif command == "run-learning-cycle":
        return await run_learning_cycle(SeedRequest())

    elif command == "boot-skill":
        return await boot_skill()

    elif command == "skill-reflect":
        return await skill_reflect()

    elif command == "goal":
        return await get_goals()

    elif command == "status":
        return await get_status()

    else:
        raise HTTPException(status_code=404, detail=f"Unknown command: {command}")

# ------------------------------
# Optional: Suggest Commands for Autocomplete
# ------------------------------

@router.post("/suggest")
async def suggest_commands(payload: dict):
    query = payload.get("query", "").lower()
    commands = ["run-dream", "run-learning-cycle", "boot-skill", "skill-reflect", "goal", "status", "help"]
    filtered = [cmd for cmd in commands if query in cmd]
    return {"suggestions": filtered}