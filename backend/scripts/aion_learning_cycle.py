import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

# Explicitly load from project root
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

# --- AION Modules ---
from modules.hexcore.memory_engine import MemoryEngine
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.memory_reflector import MemoryReflector
from modules.hexcore.ai_wallet import AIWallet
from modules.skills.boot_selector import BootSelector
from modules.skills.strategy_planner import StrategyPlanner
from modules.skills.goal_engine import GoalEngine  # <-- Added GoalEngine import
from modules.consciousness.reflection_engine import ReflectionEngine
from modules.skills.boot_archiver import archive_learned_skills

# Optional: Seed an idea into memory
def seed_memory(content: str, label_prefix="manual_seed"):
    memory = MemoryEngine()
    label = f"{label_prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    memory.store({
        "label": label,
        "content": content.strip()
    })
    print(f"✅ Seeded memory: {label}")
    return label

# Add milestone and create linked goals from strategies
def process_milestones_and_goals(strategies_with_ids):
    tracker = MilestoneTracker()
    goal_engine = GoalEngine()

    # For each strategy, create a milestone and goal linked to that strategy ID
    for strategy in strategies_with_ids:
        strat_id = strategy.get("id")
        goal_text = strategy.get("goal")

        if strat_id is None:
            print(f"⚠️ Strategy missing 'id', skipping milestone and goal creation for strategy: {strategy}")
            continue

        # Add milestone with strategy goal text as excerpt for traceability
        milestone_name = f"milestone_for_{strat_id[:8]}"
        tracker.add_milestone(
            name=milestone_name,
            excerpt=f"Derived from strategy goal: {goal_text}",
            source="strategy_generated"
        )

        # Create a linked goal in GoalEngine referencing this strategy ID
        goal_engine.create_goal_from_milestone(
            milestone_name,
            description=f"Goal linked to strategy ID {strat_id}: {goal_text}",
            reward=5,
            priority=5,
            origin_strategy_id=strat_id
        )

        print(f"🔗 Linked strategy ID {strat_id} to milestone '{milestone_name}' and created corresponding goal.")

# Reflection step
def reflect_memories():
    print("🔍 Running reflection...")
    try:
        reflector = MemoryReflector()
        reflector.reflect()
    except Exception as e:
        print(f"⚠️ Error during reflection: {e}")

# Token reward logic
def reward_tokens(amount=10, token="STK"):
    wallet = AIWallet()
    wallet.earn(token, amount)
    print(f"🪙 Minted {amount} ${token} to AION wallet.")

# Generate strategies with IDs and process them for goals and milestones
def generate_and_process_strategies():
    planner = StrategyPlanner()
    planner.generate_with_ids()  # Generate strategies with IDs

    # Pass generated strategies to milestone and goal processors
    process_milestones_and_goals(planner.strategies)

# Try loading a boot skill from recent memory
def try_boot_skill_from_memory():
    memory = MemoryEngine()
    boot_selector = BootSelector()
    all_memories = memory.get_all()
    recent = all_memories[-1:] if all_memories else []

    if not recent:
        print("⚠️ No memory to match.")
        return

    dream = recent[0].get("content", "")
    skill = boot_selector.find_matching_skill(dream)
    if skill:
        print(f"🚀 Skill match found: {skill['title']} (tags: {', '.join(skill.get('tags', []))})")
    else:
        print("🛑 No boot skill matched from last memory.")

# Optional deeper reflection summary
def run_reflection_engine():
    engine = ReflectionEngine()
    summary = engine.run(limit=5)
    print("🪞 Reflection Output:\n", summary)

# Full Loop Trigger
def run_aion_learning_cycle():
    print("✨ Starting AION Learning Cycle...")

    # Step 1: Seed memory (optional)
    seed_memory("AION should explore swarm intelligence for decentralized agent coordination.")

    # Step 2: Reflect + detect milestones
    reflect_memories()

    # Step 3: Reward tokens
    reward_tokens(10)

    # Step 4: Generate strategies with IDs and create linked milestones + goals
    generate_and_process_strategies()

    # Step 5: Try boot skill match
    try_boot_skill_from_memory()

    # Step 6: Optional deeper reflection
    run_reflection_engine()

    # Step 7: Archive learned skills
    archive_learned_skills()

    print("✅ AION Learning Cycle Complete.")

# Run the learning cycle
if __name__ == "__main__":
    run_aion_learning_cycle()