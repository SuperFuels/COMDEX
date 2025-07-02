from apscheduler.schedulers.background import BackgroundScheduler
from modules.skills.strategy_planner import StrategyPlanner
from modules.hexcore.memory_engine import MemoryEngine
import time

planner = StrategyPlanner()
memory = MemoryEngine()
scheduler = BackgroundScheduler()

def run_goal_loop():
    print("🔁 Running AION Goal Loop...")
    goal = planner.generate_goal()

    memory.store({
        "label": f"auto_goal_{goal[:20].replace(' ', '_')}",  # generate a short unique label
        "content": goal
    })
    print(f"🎯 Stored Goal: {goal}")

# ⏱️ SAFER INTERVAL: Run every 5 minutes
scheduler.add_job(run_goal_loop, 'interval', minutes=5)
scheduler.start()

# Optional idle loop for dev servers
if __name__ == "__main__":
    try:
        while True:
            time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()