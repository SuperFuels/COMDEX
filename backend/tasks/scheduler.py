import os
import subprocess
import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.strategy_planner import StrategyPlanner

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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

def run_finance_recurring_work():
    """Run due read-only Finance schedules for every canonical business container."""
    try:
        from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
        from backend.modules.aion_business.runtime.finance_recurring_work_service import FinanceRecurringWorkService
        from backend.modules.aion_business.runtime.paths import AIONBusinessPaths

        root = AIONBusinessPaths.BUSINESS_CONTAINERS
        if not root.exists():
            return
        for workspace in sorted(path for path in root.iterdir() if path.is_dir()):
            try:
                results = FinanceRecurringWorkService(BusinessContainerRepository()).run_due(workspace.name)
                if results:
                    logger.info("Finance recurring work %s: %s", workspace.name, results)
            except Exception:
                logger.exception("Finance recurring scheduler failed for %s", workspace.name)
    except Exception:
        logger.exception("Finance recurring scheduler scan failed")

def run_pilot_scheduled_work():
    """Run due governed Pilot jobs without bypassing their action boundaries."""
    try:
        from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
        from backend.modules.aion_business.runtime.pilot_scheduled_work_service import PilotScheduledWorkService

        root = AIONBusinessPaths.BUSINESS_CONTAINERS
        if not root.exists():
            return
        service = PilotScheduledWorkService()
        for workspace in sorted(path for path in root.iterdir() if path.is_dir()):
            try:
                results = service.run_due(workspace.name)
                if results:
                    logger.info("Pilot scheduled work %s: %s", workspace.name, results)
            except Exception:
                logger.exception("Pilot scheduled-work scan failed for %s", workspace.name)
    except Exception:
        logger.exception("Pilot scheduled-work scheduler scan failed")

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
        # Durable schedule records decide whether work is due; this job only owns the scan.
        scheduler.add_job(
            run_finance_recurring_work,
            CronTrigger(minute="*/5"),
            id="aion-finance-recurring-work",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.add_job(
            run_pilot_scheduled_work,
            CronTrigger(minute="*"),
            id="aion-pilot-scheduled-work",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        scheduler.start()
        logger.info("✅ Dream + Goal scheduler started.")

        atexit.register(lambda: scheduler.shutdown(wait=False))
    else:
        logger.info("🔁 Scheduler already running.")
