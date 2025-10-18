"""
AION Dual Heartbeat Orchestrator
────────────────────────────────────────────
Supervises and sustains the AION Fabric core using a dual redundant
heartbeat model (Primary ⇄ Mirror).

• Primary runs full Fabric (receiver + stream + feedback + dashboard).
• Mirror monitors the Primary via REST pings and can assume control
  if Primary is unresponsive for N cycles.
────────────────────────────────────────────
"""

import os
import sys
import json
import time
import signal
import logging
import threading
import requests
import subprocess
from argparse import ArgumentParser
from flask import Flask, request, jsonify
from logging.handlers import RotatingFileHandler

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
HEARTBEAT_INTERVAL = 3.0  # seconds
FAIL_THRESHOLD = 3         # missed beats before takeover
STATE_FILE = "backend/logs/aion_dual_state.json"

PRIMARY_PORT = 5090
MIRROR_PORT = 6090

# Optional: cross-system communication setup
MIRROR_HOST = os.getenv("MIRROR_HOST", f"http://127.0.0.1:{MIRROR_PORT}")
AUTH_TOKEN = os.getenv("AION_HEART_TOKEN", None)

SERVICES = {
    "receiver": "backend/AION/fabric/fabric_stream_receiver.py",
    "stream": "backend/AION/fabric/aion_fabric_stream.py",
    "feedback": "backend/AION/fabric/aion_fabric_feedback.py",
    "dashboard": "backend/AION/fabric/fabric_stream_dashboard.py",
}

LOG_PATH = "backend/logs/aion_dual_heartbeat.log"
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# ────────────────────────────────────────────────
# Logging setup
# ────────────────────────────────────────────────
logger = logging.getLogger("AIONDualHeartbeat")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")

console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────
def safe_post(url, payload):
    """Send POST safely with optional auth header."""
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    try:
        return requests.post(url, json=payload, headers=headers, timeout=2)
    except Exception:
        return None


def safe_get(url):
    """GET request that fails silently."""
    try:
        return requests.get(url, timeout=2)
    except Exception:
        return None


# ────────────────────────────────────────────────
# Local Fabric Supervisor (Primary & Mirror)
# ────────────────────────────────────────────────
class AIONSupervisor:
    def __init__(self, role):
        self.role = role
        self.processes = {}
        self.lock = threading.Lock()

    def start_service(self, name, cmd):
        logger.info(f"[{self.role}] ▶ Starting {name} …")
        proc = subprocess.Popen(["python", cmd])
        with self.lock:
            self.processes[name] = proc

    def start_all(self):
        logger.info(f"[{self.role}] 💠 Starting full AION Fabric suite …")
        for name, cmd in SERVICES.items():
            self.start_service(name, cmd)
            time.sleep(1)

    def stop_all(self):
        logger.info(f"[{self.role}] ⏹️ Stopping all services …")
        with self.lock:
            for proc in self.processes.values():
                if proc.poll() is None:
                    proc.terminate()
            time.sleep(2)
            for proc in self.processes.values():
                if proc.poll() is None:
                    proc.kill()
            self.processes.clear()
        logger.info(f"[{self.role}] ✅ Services stopped.")


# ────────────────────────────────────────────────
# Primary heartbeat loop
# ────────────────────────────────────────────────
def primary_loop():
    sup = AIONSupervisor("Primary")
    sup.start_all()
    logger.info(f"[Primary] 💓 Heartbeat active; broadcasting to {MIRROR_HOST}")

    while True:
        payload = {"role": "primary", "status": "alive", "timestamp": time.time()}
        safe_post(f"{MIRROR_HOST}/heartbeat/state", payload)

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        time.sleep(HEARTBEAT_INTERVAL)


# ────────────────────────────────────────────────
# Mirror heartbeat receiver and monitor
# ────────────────────────────────────────────────
app = Flask(__name__)
mirror_state = {"last_seen": 0, "primary_alive": False, "takeover": False}
mirror_lock = threading.Lock()


@app.route("/heartbeat/state", methods=["POST"])
def receive_state():
    """Receive heartbeat ping from primary node."""
    data = request.get_json(force=True)
    with mirror_lock:
        mirror_state["last_seen"] = time.time()
        mirror_state["primary_alive"] = True
        mirror_state["takeover"] = False
    logger.debug(f"[Mirror] Pulse received from Primary @ {data.get('timestamp')}")
    return jsonify({"status": "ok"}), 200


@app.route("/heartbeat/status", methods=["GET"])
def mirror_status():
    """Expose mirror state for remote health checks."""
    with mirror_lock:
        delta = time.time() - mirror_state["last_seen"]
    return jsonify({
        "primary_alive": mirror_state["primary_alive"],
        "time_since_last": round(delta, 2),
        "takeover": mirror_state["takeover"]
    }), 200


def mirror_loop():
    """Continuously monitor Primary's health."""
    fails = 0
    takeover_proc = None
    sup = AIONSupervisor("Mirror")

    logger.info(f"[Mirror] 🩶 Monitoring primary on port {PRIMARY_PORT} …")

    while True:
        time.sleep(HEARTBEAT_INTERVAL)

        with mirror_lock:
            delta = time.time() - mirror_state["last_seen"]

        # Primary missed beat
        if delta > HEARTBEAT_INTERVAL * FAIL_THRESHOLD:
            fails += 1
            logger.warning(f"[Mirror] ⚠️ Missed heartbeat ({fails}/{FAIL_THRESHOLD})")
        else:
            fails = 0

        # Takeover trigger
        if fails >= FAIL_THRESHOLD and not mirror_state["takeover"]:
            logger.warning("[Mirror] 🚨 Primary unresponsive — initiating takeover.")
            mirror_state["takeover"] = True
            sup.start_all()

        # Recovery detection
        if mirror_state["takeover"] and delta < HEARTBEAT_INTERVAL * 2:
            logger.info("[Mirror] 🌅 Primary restored — yielding control.")
            sup.stop_all()
            mirror_state["takeover"] = False
            fails = 0


def run_mirror():
    threading.Thread(target=mirror_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=MIRROR_PORT)


# ────────────────────────────────────────────────
# Main Entry
# ────────────────────────────────────────────────
def main():
    parser = ArgumentParser()
    parser.add_argument("--role", choices=["primary", "mirror"], default="primary")
    args = parser.parse_args()

    role = args.role.lower()
    logger.info(f"🚀 Launching AION Dual Heartbeat as {role.upper()}")

    def shutdown(signum, frame):
        logger.info(f"[{role}] Shutting down heartbeat.")
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    if role == "primary":
        primary_loop()
    else:
        run_mirror()


if __name__ == "__main__":
    main()

# ────────────────────────────────────────────────
# Deployment Notes
# ────────────────────────────────────────────────
"""
To deploy on separate systems:

1. On Primary host (System A):
   export MIRROR_HOST="http://mirror-host:6090"
   python backend/AION/system/aion_dual_heartbeat.py --role primary

2. On Mirror host (System B):
   python backend/AION/system/aion_dual_heartbeat.py --role mirror

3. To secure the link:
   export AION_HEART_TOKEN="super_secret"
   Uncomment AUTH_TOKEN in safe_post().
   Both systems must share the same token.

4. For local testing:
   Run both nodes on same machine.
   Mirror automatically detects primary downtime and takes over.
"""