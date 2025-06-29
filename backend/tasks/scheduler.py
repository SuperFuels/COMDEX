from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess
import atexit
import os

scheduler = None  # Track scheduler globally to avoid duplicate starts

def run_dream_cycle():
    print("🌙 Running AION nightly dream cycle...")
    subprocess.run(["python", "backend/modules/skills/dream_core.py"])

def start_scheduler():
    global scheduler

    # Avoid running scheduler in test or migration environments
    if os.getenv("ENV", "").lower() == "test":
        print("⚠️ Scheduler disabled in test environment.")
        return

    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_dream_cycle, CronTrigger(hour=3, minute=0))  # 🕒 3AM UTC
        scheduler.start()
        print("✅ Dream scheduler started.")
        atexit.register(lambda: scheduler.shutdown())
    else:
        print("🔁 Scheduler already running.")