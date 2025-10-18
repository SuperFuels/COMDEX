"""
AION Heartbeat Orchestrator
────────────────────────────────────────────
Supervises and sustains the AION Fabric core:
Receiver ⇄ Stream ⇄ Feedback ⇄ Dashboard ⇄ Simulator

Provides continuous health monitoring, auto-restart,
log rotation, and groundwork for dual heartbeat redundancy.
"""

import subprocess
import time
import os
import signal
import logging
import threading
import requests
import json
from typing import Dict, Optional
from logging.handlers import RotatingFileHandler

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
SERVICES = {
    "receiver": "backend/AION/fabric/fabric_stream_receiver.py",
    "stream": "backend/AION/fabric/aion_fabric_stream.py",
    "feedback": "backend/AION/fabric/aion_fabric_feedback.py",
    "dashboard": "backend/AION/fabric/fabric_stream_dashboard.py",
    "simulator": "backend/tests/test_fabric_stream_heartbeat.py",
}

HEALTH_ENDPOINTS = {
    "receiver": "http://127.0.0.1:5090/fabric/all",
    "dashboard": "http://127.0.0.1:8050",
}

LOG_PATH = "backend/logs/aion_heartbeat.log"
STATE_FILE = "/tmp/aion_heartbeat_state.json"
CHECK_INTERVAL = 5.0
RESTART_DELAY = 3.0

# ────────────────────────────────────────────────
# Logging setup with rotation
# ────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger = logging.getLogger("AIONHeartbeat")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")

# Console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# File output with rotation
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ────────────────────────────────────────────────
# Process management
# ────────────────────────────────────────────────
class HeartbeatSupervisor:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.lock = threading.Lock()
        self.running = True
        self.state: Dict[str, Dict] = {}

    def start_service(self, name: str, cmd: str):
        """Start a single service."""
        logger.info(f"[AIONHeartbeat] ▶ Starting {name} …")
        proc = subprocess.Popen(
            ["python", cmd],
            stdout=open(os.devnull, "w"),  # discard Flask logs
            stderr=open(os.devnull, "w"),
            cwd=os.getcwd(),  # ensure correct working directory
        )
        self.processes[name] = proc
        self.state[name] = {"status": "running", "pid": proc.pid, "restarts": 0}

    def check_service(self, name: str):
        """Check if service is alive; restart if necessary."""
        proc = self.processes.get(name)
        if not proc:
            return

        # If process exited
        if proc.poll() is not None:
            logger.warning(f"[AIONHeartbeat] ⚠️ {name} terminated. Restarting …")
            self.restart_service(name)
            return

        # Health probe if endpoint is defined
        endpoint = HEALTH_ENDPOINTS.get(name)
        if endpoint:
            try:
                resp = requests.get(endpoint, timeout=2)
                if resp.status_code != 200:
                    raise Exception(f"bad status {resp.status_code}")
                self.state[name]["status"] = "healthy"
            except Exception as e:
                logger.warning(f"[AIONHeartbeat] ⚠️ {name} unresponsive: {e}")
                self.restart_service(name)

    def restart_service(self, name: str):
        """Restart a service after failure."""
        proc = self.processes.get(name)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        time.sleep(RESTART_DELAY)
        logger.info(f"[AIONHeartbeat] 🔁 Restarting {name} …")
        self.start_service(name, SERVICES[name])
        self.state[name]["restarts"] += 1

    def update_state_file(self):
        """Write live state to JSON file."""
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"[AIONHeartbeat] Failed to write state: {e}")

    def monitor_loop(self):
        """Continuously check and maintain services."""
        while self.running:
            with self.lock:
                for name in list(self.processes.keys()):
                    self.check_service(name)
                self.update_state_file()
            time.sleep(CHECK_INTERVAL)

    def stop_all(self):
        """Graceful shutdown."""
        logger.info("[AIONHeartbeat] ⏹️ Stopping all services …")
        self.running = False
        for proc in self.processes.values():
            if proc.poll() is None:
                proc.terminate()
        time.sleep(2)
        for proc in self.processes.values():
            if proc.poll() is None:
                proc.kill()
        logger.info("[AIONHeartbeat] ✅ All services stopped.")

# ────────────────────────────────────────────────
# Mirror Heartbeat Thread (prototype)
# ────────────────────────────────────────────────
def mirror_thread():
    """Monitors primary heartbeat health (stub for Stage-2)."""
    while True:
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    state = json.load(f)
                health = all(v.get("status") == "healthy" for v in state.values())
                if not health:
                    logger.warning("[AIONMirror] ⚠️ Primary health degraded.")
            else:
                logger.warning("[AIONMirror] No primary state file found.")
        except Exception:
            pass
        time.sleep(10)

# ────────────────────────────────────────────────
# Main orchestrator
# ────────────────────────────────────────────────
def run_heartbeat():
    hb = HeartbeatSupervisor()

    # Start core services
    hb.start_service("receiver", SERVICES["receiver"])
    time.sleep(1)
    hb.start_service("stream", SERVICES["stream"])
    time.sleep(1)
    hb.start_service("feedback", SERVICES["feedback"])
    time.sleep(1)

    # Optional dashboard + simulator (simulator ON by default)
    if os.environ.get("AION_DASHBOARD", "1") == "1":
        hb.start_service("dashboard", SERVICES["dashboard"])
    if os.environ.get("AION_SIMULATOR", "1") == "1":
        hb.start_service("simulator", SERVICES["simulator"])

    # Start monitoring thread
    t = threading.Thread(target=hb.monitor_loop, daemon=True)
    t.start()

    # Mirror monitoring (for redundancy)
    threading.Thread(target=mirror_thread, daemon=True).start()

    # Handle SIGINT/SIGTERM
    def shutdown_handler(signum, frame):
        hb.stop_all()
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("💓 AION Heartbeat running — supervising all core processes.")
    while True:
        time.sleep(30)

if __name__ == "__main__":
    run_heartbeat()