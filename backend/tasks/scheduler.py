from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess
import atexit

def run_dream_cycle():
    print("🌙 Running AION nightly dream cycle...")
    subprocess.run(["python", "backend/modules/skills/dream_core.py"])

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_dream_cycle, CronTrigger(hour=3, minute=0))  # ⏰ Run every night at 3AM
    scheduler.start()
    print("✅ Dream scheduler started.")
    atexit.register(lambda: scheduler.shutdown())
