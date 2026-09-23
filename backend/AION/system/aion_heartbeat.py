#!/usr/bin/env python3
"""
AION Heartbeat Orchestrator - v2.3
────────────────────────────────────────────
Supervises and sustains the AION Fabric Core:
Receiver ⇄ Stream ⇄ Feedback ⇄ Dashboard ⇄ Simulator

Features:
 * Continuous health monitoring + auto-restart
 * Rotating logs and JSON state file
 * Restart cooldowns and safe counter updates
 * Optional quiet mode (AION_QUIET_MODE=1)
 * Stage-2 mirror redundancy (prototype)
"""

import subprocess
import time
import os
import sys
import signal
import logging
import threading
import requests
import json
import tempfile
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
    "cognitive_runtime": "backend/AION/system/aion_cognitive_runtime_service.py",
    "outcome_learning": "backend/AION/system/aion_real_outcome_learning_service.py",
    "general_apprentice": "backend/AION/system/aion_general_apprentice_service.py",
    "north_star_mastery": "backend/AION/system/aion_north_star_mastery_service.py",
    "mastery_curriculum": "backend/AION/system/aion_mastery_curriculum_service.py",
    "open_mission_compounding": "backend/AION/system/aion_open_mission_compounding_service.py",
    "open_mission_executor": "backend/AION/system/aion_open_mission_executor_service.py",
    "long_duration_campaign": "backend/AION/system/aion_long_duration_real_outcome_campaign_service.py",
}

LIVE_SERVICE_STATUSES = {"healthy", "running"}


def unhealthy_services(state: dict) -> list[str]:
    """Return services that are not currently live.

    Process-backed services report ``running`` while HTTP-backed services report
    ``healthy``. Both states represent a live primary service.
    """
    return [
        name
        for name, service_state in state.items()
        if service_state.get("status") not in LIVE_SERVICE_STATUSES
    ]

HEALTH_ENDPOINTS = {
    "receiver": "http://127.0.0.1:5090/fabric/all",
    "dashboard": "http://127.0.0.1:8050",
}

LOG_PATH = "backend/logs/aion_heartbeat.log"
STATE_FILE = "/tmp/aion_heartbeat_state.json"
CHECK_INTERVAL = 5.0
RESTART_DELAY = 3.0
RESTART_COOLDOWN = 30.0  # seconds between restarts per service

# ────────────────────────────────────────────────
# Logging setup with rotation
# ────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger = logging.getLogger("AIONHeartbeat")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Quiet mode disables console spam
if os.environ.get("AION_QUIET_MODE", "0") == "1":
    stream_handler.setLevel(logging.ERROR)

logger.addHandler(stream_handler)

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ────────────────────────────────────────────────
# Process Supervisor
# ────────────────────────────────────────────────
class HeartbeatSupervisor:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.lock = threading.Lock()
        self.running = True
        self.state: Dict[str, Dict] = {}
        self.last_restart: Dict[str, float] = {}

    def start_service(self, name: str, cmd: str):
        """Start a single service."""
        try:
            logger.info(f"[AIONHeartbeat] ▶ Starting {name} ...")
            proc = subprocess.Popen(
                [sys.executable, cmd],
                stdout=open(os.devnull, "w"),
                stderr=open(os.devnull, "w"),
                cwd=os.getcwd(),
            )
            self.processes[name] = proc
            self.state[name] = {
                "status": "running",
                "pid": proc.pid,
                "restarts": self.state.get(name, {}).get("restarts", 0),
            }
        except Exception as e:
            logger.error(f"[AIONHeartbeat] ❌ Failed to start {name}: {e}")

    def check_service(self, name: str):
        """Check if a service is healthy or restart if unresponsive."""
        proc = self.processes.get(name)
        if not proc:
            return

        # If process exited
        if proc.poll() is not None:
            logger.warning(f"[AIONHeartbeat] ⚠️ {name} terminated. Restarting ...")
            self.restart_service(name)
            return

        # Health probe if endpoint is defined
        endpoint = HEALTH_ENDPOINTS.get(name)
        if endpoint:
            try:
                resp = requests.get(endpoint, timeout=2)
                if resp.status_code == 200:
                    self.state[name]["status"] = "healthy"
                else:
                    raise Exception(f"Bad status {resp.status_code}")
            except Exception as e:
                logger.warning(f"[AIONHeartbeat] ⚠️ {name} unresponsive: {e}")
                self.restart_service(name)

    def restart_service(self, name: str):
        """Restart a service after failure, respecting cooldown."""
        now = time.time()
        if now - self.last_restart.get(name, 0) < RESTART_COOLDOWN:
            logger.info(f"[AIONHeartbeat] ⏳ Cooldown active - skipping rapid restart of {name}")
            return
        self.last_restart[name] = now

        proc = self.processes.get(name)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()

        time.sleep(RESTART_DELAY)
        logger.info(f"[AIONHeartbeat] 🔁 Restarting {name} ...")
        self.start_service(name, SERVICES[name])
        self.state.setdefault(name, {"restarts": 0})
        self.state[name]["restarts"] += 1

    def update_state_file(self):
        """Write live state to JSON file."""
        temporary_path = None
        try:
            state_directory = os.path.dirname(STATE_FILE) or "."
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=state_directory,
                prefix=".aion_heartbeat_state.",
                suffix=".tmp",
                delete=False,
            ) as f:
                temporary_path = f.name
                json.dump(self.state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, STATE_FILE)
            temporary_path = None
        except Exception as e:
            logger.warning(f"[AIONHeartbeat] Failed to write state: {e}")
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

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
        logger.info("[AIONHeartbeat] ⏹️ Stopping all services ...")
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
# Mirror Heartbeat (Stage-2)
# ────────────────────────────────────────────────
def mirror_thread():
    """Monitors primary heartbeat health (Stage-2 redundancy stub)."""
    while True:
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    state = json.load(f)
                unhealthy = unhealthy_services(state)
                if unhealthy:
                    logger.warning(f"[AIONMirror] ⚠️ Primary health degraded: {unhealthy}")
            else:
                logger.warning("[AIONMirror] No primary state file found.")
        except Exception as e:
            logger.warning(f"[AIONMirror] Mirror thread error: {e}")
        time.sleep(10)

# ────────────────────────────────────────────────
# Main Entry
# ────────────────────────────────────────────────
def run_heartbeat():
    hb = HeartbeatSupervisor()

    # The legacy Fabric demo services are not part of the open-mission learner.
    # They used to start unconditionally, even on installations where their
    # receiver/dashboard immediately exited and entered a restart loop.  Keep
    # them available for explicit Fabric work without charging every desktop
    # boot for them.
    if os.environ.get("AION_FABRIC_CORE", "0") == "1":
        for name in ("receiver", "stream", "feedback"):
            hb.start_service(name, SERVICES[name])
            time.sleep(1)

    # Optional modules
    if os.environ.get("AION_DASHBOARD", "0") == "1":
        hb.start_service("dashboard", SERVICES["dashboard"])
    if os.environ.get("AION_SIMULATOR", "0") == "1":
        hb.start_service("simulator", SERVICES["simulator"])
    # Open-mission compounding is the current governed learning authority.  The
    # older canonical cognitive runtime is opt-in because its neural startup can
    # consume every CPU core while duplicating work already owned below.
    if os.environ.get("AION_COGNITIVE_RUNTIME", "0") == "1":
        hb.start_service("cognitive_runtime", SERVICES["cognitive_runtime"])
    # The installed LaunchAgent is the canonical owner of outcome learning.
    # Set this explicitly to 1 only in installations without that supervisor.
    if os.environ.get("AION_OUTCOME_LEARNING", "0") == "1":
        hb.start_service("outcome_learning", SERVICES["outcome_learning"])
    if os.environ.get("AION_GENERAL_APPRENTICE", "1") == "1":
        hb.start_service("general_apprentice", SERVICES["general_apprentice"])
    if os.environ.get("AION_NORTH_STAR_MASTERY", "1") == "1":
        hb.start_service("north_star_mastery", SERVICES["north_star_mastery"])
        hb.start_service("mastery_curriculum", SERVICES["mastery_curriculum"])
    if os.environ.get("AION_OPEN_MISSION_COMPOUNDING", "1") == "1":
        hb.start_service("open_mission_compounding", SERVICES["open_mission_compounding"])
        hb.start_service("open_mission_executor", SERVICES["open_mission_executor"])
        # The rolling public-world mission uses this evaluator-owned ledger as
        # its later outcome authority.  Keep it under the same reboot-safe
        # supervisor so the executor cannot wait forever on a stale cursor.
        hb.start_service("long_duration_campaign", SERVICES["long_duration_campaign"])

    # Start monitoring threads
    threading.Thread(target=hb.monitor_loop, daemon=True).start()
    threading.Thread(target=mirror_thread, daemon=True).start()

    # Handle termination
    def shutdown_handler(signum, frame):
        hb.stop_all()
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("💓 AION Heartbeat running - supervising all core processes.")
    while True:
        time.sleep(30)

# ────────────────────────────────────────────────
if __name__ == "__main__":
    run_heartbeat()
