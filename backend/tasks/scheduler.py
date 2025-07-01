from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess
import atexit
import os

from modules.hexcore.memory_engine import MemoryEngine  # FIXED import here
from modules.skills.strategy_planner import StrategyPlanner

scheduler = None  # Global scheduler to avoid duplicate starts

memory_engine = MemoryEngine()
planner = StrategyPlanner()

def run_dream_cycle():
    print("🌙 Running AION nightly dream cycle...")
    subprocess.run(["python", "backend/modules/skills/dream_core.py"])

def run_goal_loop():
    print("🎯 Generating next AION goal...")
    new_goal = planner.generate_goal()
    memory_engine.store_memory({
        "source": "goal-loop",
        "type": "auto-generated",
        "content": new_goal
    })
    print(f"✅ Stored Goal: {new_goal}")

def start_scheduler():
    global scheduler

    # Avoid running in test/migration containers
    if os.getenv("ENV", "").lower() == "test":
        print("⚠️ Scheduler disabled in test environment.")
        return

    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_dream_cycle, CronTrigger(hour=3, minute=0))      # 🕒 3AM UTC
        scheduler.add_job(run_goal_loop, CronTrigger(minute='*/10'))           # 🔁 Every 10 mins
        scheduler.start()
        print("✅ Dream + Goal scheduler started.")
        atexit.register(lambda: scheduler.shutdown())
    else:
        print("🔁 Scheduler already running.")