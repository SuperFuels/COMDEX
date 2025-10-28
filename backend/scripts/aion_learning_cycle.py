import os
import json
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load from project root
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

# --- AION Modules ---
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

def log(msg: str):
    print(f"[AION-LEARNING] {msg}")

def seed_memory(content: str, label_prefix="manual_seed"):
    memory = MemoryEngine()
    label = f"{label_prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    memory.store({"label": label, "content": content.strip()})
    log(f"✅ Seeded memory: {label}")
    return label

def process_milestones_and_goals(strategies_with_ids):
    tracker = MilestoneTracker()
    goal_engine = GoalEngine()
    created = 0

    for strategy in strategies_with_ids:
        strat_id = strategy.get("id")
        goal_text = strategy.get("goal")

        if strat_id is None:
            log(f"⚠️ Strategy missing 'id', skipping: {strategy}")
            continue

        milestone_name = f"milestone_for_{strat_id[:8]}"
        tracker.add_milestone(
            name=milestone_name,
            excerpt=f"Derived from strategy goal: {goal_text}",
            source="strategy_generated"
        )

        goal_engine.create_goal_from_milestone(
            milestone_name,
            description=f"Goal linked to strategy ID {strat_id}: {goal_text}",
            reward=5,
            priority=5,
            origin_strategy_id=strat_id
        )

        log(f"🔗 Linked strategy ID {strat_id} → milestone '{milestone_name}' + goal")
        created += 1
    return created

def reflect_memories():
    log("🔍 Reflecting on memory...")
    try:
        reflector = MemoryReflector()
        reflector.reflect()
    except Exception as e:
        log(f"⚠️ Reflection error: {e}")

def reward_tokens(amount=10, token="STK"):
    wallet = AIWallet()
    wallet.earn(token, amount)
    log(f"🪙 Minted {amount} ${token} to AION wallet.")

def generate_and_process_strategies():
    planner = StrategyPlanner()
    planner.generate_with_ids()
    created = process_milestones_and_goals(planner.strategies)
    return created

def try_boot_skill_from_memory():
    memory = MemoryEngine()
    boot_selector = BootSelector()
    all_memories = memory.get_all()
    recent = all_memories[-1:] if all_memories else []

    if not recent:
        log("⚠️ No memory to match.")
        return False

    dream = recent[0].get("content", "")
    skill = boot_selector.find_matching_skill(dream)
    if skill:
        log(f"🚀 Skill match found: {skill['title']} (tags: {', '.join(skill.get('tags', []))})")
        return True
    else:
        log("🛑 No boot skill matched from last memory.")
        return False

def run_reflection_engine():
    try:
        engine = ReflectionEngine()
        summary = engine.run(limit=5)
        log("🪞 Reflection Summary:\n" + summary)
    except Exception as e:
        log(f"⚠️ ReflectionEngine error: {e}")

def run_aion_learning_cycle(seed_text):
    log("✨ Starting AION Learning Cycle...")
    result = {"status": "started", "boot_skill_match": False, "milestones_created": 0, "tokens_minted": 0}

    try:
        seed_memory(seed_text)
        reflect_memories()
        reward_tokens(10)
        result["tokens_minted"] = 10
        result["milestones_created"] = generate_and_process_strategies()
        result["boot_skill_match"] = try_boot_skill_from_memory()
        run_reflection_engine()
        archive_learned_skills()
        result["status"] = "complete"
    except Exception as e:
        result["status"] = f"error: {str(e)}"
        log(f"❌ Error in learning cycle: {e}")

    log("✅ AION Learning Cycle Complete.")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=str, default="AION should explore swarm intelligence for decentralized agent coordination.")
    args = parser.parse_args()
    run_aion_learning_cycle(args.seed)