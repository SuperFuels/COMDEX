import os
import subprocess
import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.strategy_planner import StrategyPlanner

logger = logging.getLogger("comdex.scheduler")

memory_engine = MemoryEngine()
planner = StrategyPlanner()
scheduler = None  # Global singleton scheduler

def run_dream_cycle():
    logger.info("🌙 Running AION nightly dream cycle...")
    try:
        # Use subprocess to run dream_core.py (adjust path as needed)
        result = subprocess.run(
            ["python", "backend/modules/skills/dream_core.py"],
            capture_output=True, text=True, check=True
        )
        logger.info(f"Dream cycle output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Dream cycle failed: {e.stderr}")

def run_goal_loop():
    logger.info("🎯 Generating next AION goal...")
    try:
        new_goal = planner.generate_goal()
        memory_engine.store({
            "label": "auto_goal_" + new_goal[:20].replace(" ", "_"),
            "source": "goal-loop",
            "type": "auto-generated",
            "content": new_goal
        })
        logger.info(f"✅ Stored Goal: {new_goal}")
    except Exception as e:
        logger.error(f"Goal loop error: {e}")

def start_scheduler():
    global scheduler

    # Disable scheduler if running in test or migration environment
    if os.getenv("ENV", "").lower() in ("test", "migration"):
        logger.warning("⚠️ Scheduler disabled in test or migration environment.")
        return

    if scheduler is None:
        scheduler = BackgroundScheduler()

        # Schedule dream cycle daily at 3AM UTC
        scheduler.add_job(run_dream_cycle, CronTrigger(hour=3, minute=0))
        # Schedule goal loop every 10 minutes
        scheduler.add_job(run_goal_loop, CronTrigger(minute="*/10"))

        scheduler.start()
        logger.info("✅ Dream + Goal scheduler started.")

        atexit.register(lambda: scheduler.shutdown(wait=False))
    else:
        logger.info("🔁 Scheduler already running.")