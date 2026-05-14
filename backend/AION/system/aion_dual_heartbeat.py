"""
AION Dual Heartbeat Orchestrator
────────────────────────────────────────────
Supervises and sustains the AION Fabric core using a dual redundant
heartbeat model (Primary ⇄ Mirror).

* Primary runs full Fabric (receiver + stream + feedback + dashboard).
* Mirror monitors the Primary via REST pings and can assume control
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
import atexit
from argparse import ArgumentParser
from flask import Flask, request, jsonify
from logging.handlers import RotatingFileHandler

# ────────────────────────────────────────────────
# Configuration (env-overridable)
# ────────────────────────────────────────────────
HEARTBEAT_INTERVAL = float(os.getenv("AION_HEARTBEAT_INTERVAL", "3.0"))  # seconds
FAIL_THRESHOLD = int(os.getenv("AION_HEART_FAIL_THRESHOLD", "3"))       # missed beats before takeover
STATE_FILE = os.getenv("AION_HEART_STATE_FILE", "backend/logs/aion_dual_state.json")

PRIMARY_PORT = int(os.getenv("AION_HEART_PRIMARY_PORT", "5090"))
MIRROR_PORT = int(os.getenv("AION_HEART_MIRROR_PORT", "6090"))

# Optional: cross-system communication setup
MIRROR_HOST = os.getenv("MIRROR_HOST", f"http://127.0.0.1:{MIRROR_PORT}")
AUTH_TOKEN = os.getenv("AION_HEART_TOKEN", None)

# Prevent duplicate orchestrators per role (especially under reload / double-start)
PID_DIR = os.getenv("AION_HEART_PID_DIR", "/tmp")

# Fabric suite (can be disabled for dev / when running in-process elsewhere)
ENABLE_FABRIC_SUITE = os.getenv("AION_ENABLE_FABRIC_SUITE", "1").lower() in {"1", "true", "yes", "on"}

SERVICES = {
    "receiver": "backend/AION/fabric/fabric_stream_receiver.py",
    "stream": "backend/AION/fabric/aion_fabric_stream.py",
    "feedback": "backend/AION/fabric/aion_fabric_feedback.py",
    "dashboard": "backend/AION/fabric/fabric_stream_dashboard.py",
}

LOG_PATH = os.getenv("AION_HEART_LOG_PATH", "backend/logs/aion_dual_heartbeat.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

PYTHON_BIN = os.getenv("AION_PYTHON_BIN", sys.executable or "python")

# ────────────────────────────────────────────────
# Logging setup
# ────────────────────────────────────────────────
logger = logging.getLogger("AIONDualHeartbeat")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")

if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────
def _pid_file_for(role: str) -> str:
    return os.path.join(PID_DIR, f"aion_dual_heartbeat_{role}.pid")

def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def acquire_single_instance_lock(role: str) -> None:
    """Best-effort PID lock so reloads/double-starts don't spawn duplicate service suites."""
    pid_file = _pid_file_for(role)
    if os.path.exists(pid_file):
        try:
            old_pid = int(open(pid_file, "r", encoding="utf-8").read().strip() or "0")
        except Exception:
            old_pid = 0
        if _pid_is_alive(old_pid):
            logger.warning(f"[{role}] Another {role} orchestrator already running (pid={old_pid}). Exiting.")
            raise SystemExit(0)
        # stale pidfile
        try:
            os.remove(pid_file)
        except Exception:
            pass

    try:
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.warning(f"[{role}] Could not write pidfile {pid_file}: {e}")

    def _cleanup():
        try:
            if os.path.exists(pid_file):
                # only remove if it's ours
                try:
                    cur = int(open(pid_file, "r", encoding="utf-8").read().strip() or "0")
                except Exception:
                    cur = 0
                if cur == os.getpid():
                    os.remove(pid_file)
        except Exception:
            pass

    atexit.register(_cleanup)

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
        self.processes: dict[str, subprocess.Popen] = {}
        self.lock = threading.Lock()

    def _is_running(self, name: str) -> bool:
        with self.lock:
            proc = self.processes.get(name)
        return bool(proc) and proc.poll() is None

    def start_service(self, name, cmd):
        if not ENABLE_FABRIC_SUITE:
            logger.info(f"[{self.role}] (fabric disabled) Skipping start of {name}.")
            return

        if self._is_running(name):
            logger.info(f"[{self.role}] ⏭️ {name} already running; skipping.")
            return

        logger.info(f"[{self.role}] ▶ Starting {name} ...")

        # Route child stdout/stderr into the same rotating log to prevent console spam.
        # (Still safe if parent has stdout/stderr redirected.)
        try:
            out = open(LOG_PATH, "a", encoding="utf-8")
        except Exception:
            out = subprocess.DEVNULL

        proc = subprocess.Popen(
            [PYTHON_BIN, cmd],
            stdout=out,
            stderr=out,
            env=os.environ.copy(),
        )
        with self.lock:
            self.processes[name] = proc

    def start_all(self):
        if not ENABLE_FABRIC_SUITE:
            logger.info(f"[{self.role}] (fabric disabled) Not starting Fabric suite.")
            return

        logger.info(f"[{self.role}] 💠 Starting full AION Fabric suite ...")
        for name, cmd in SERVICES.items():
            self.start_service(name, cmd)
            time.sleep(0.5)

    def stop_all(self):
        logger.info(f"[{self.role}] ⏹️ Stopping all services ...")
        with self.lock:
            procs = list(self.processes.values())
        for proc in procs:
            try:
                if proc and proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        time.sleep(1.5)
        for proc in procs:
            try:
                if proc and proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
        with self.lock:
            self.processes.clear()
        logger.info(f"[{self.role}] ✅ Services stopped.")

# ────────────────────────────────────────────────
# Primary heartbeat loop
# ────────────────────────────────────────────────
_shutdown_flag = threading.Event()

def primary_loop():
    acquire_single_instance_lock("primary")
    sup = AIONSupervisor("Primary")
    sup.start_all()
    logger.info(f"[Primary] 💓 Heartbeat active; broadcasting to {MIRROR_HOST}")

    # graceful shutdown
    def _shutdown(*_):
        if _shutdown_flag.is_set():
            return
        _shutdown_flag.set()
        logger.info("[Primary] Shutting down heartbeat.")
        try:
            sup.stop_all()
        finally:
            os._exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        payload = {"role": "primary", "status": "alive", "timestamp": time.time()}

        # Mirror ping (best-effort)
        safe_post(f"{MIRROR_HOST}/heartbeat/state", payload)

        # State file write (best-effort)
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

        time.sleep(HEARTBEAT_INTERVAL)

# ────────────────────────────────────────────────
# Mirror heartbeat receiver and monitor
# ────────────────────────────────────────────────
app = Flask(__name__)
mirror_state = {"last_seen": 0.0, "primary_alive": False, "takeover": False}
mirror_lock = threading.Lock()

def _auth_ok(req) -> bool:
    if not AUTH_TOKEN:
        return True
    hdr = req.headers.get("Authorization", "")
    return hdr == f"Bearer {AUTH_TOKEN}"

@app.route("/heartbeat/state", methods=["POST"])
def receive_state():
    """Receive heartbeat ping from primary node."""
    if not _auth_ok(request):
        return jsonify({"status": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    now = time.time()
    with mirror_lock:
        mirror_state["last_seen"] = now
        mirror_state["primary_alive"] = True
        # if primary is pinging, we consider takeover false unless we explicitly stay in takeover mode
        if not mirror_state["takeover"]:
            mirror_state["takeover"] = False

    logger.debug(f"[Mirror] Pulse received from Primary @ {data.get('timestamp')}")
    return jsonify({"status": "ok"}), 200

@app.route("/heartbeat/status", methods=["GET"])
def mirror_status():
    """Expose mirror state for remote health checks."""
    with mirror_lock:
        delta = time.time() - float(mirror_state["last_seen"] or 0.0)
        primary_alive = bool(mirror_state["primary_alive"])
        takeover = bool(mirror_state["takeover"])
    return jsonify({
        "primary_alive": primary_alive,
        "time_since_last": round(delta, 2),
        "takeover": takeover,
    }), 200

def mirror_loop():
    """Continuously monitor Primary's health."""
    acquire_single_instance_lock("mirror")

    fails = 0
    sup = AIONSupervisor("Mirror")
    logger.info(f"[Mirror] 🩶 Monitoring primary (expected heartbeat interval={HEARTBEAT_INTERVAL}s) ...")

    while True:
        time.sleep(HEARTBEAT_INTERVAL)

        with mirror_lock:
            last = float(mirror_state["last_seen"] or 0.0)
            takeover = bool(mirror_state["takeover"])

        delta = time.time() - last

        # Primary missed beat
        if delta > HEARTBEAT_INTERVAL * FAIL_THRESHOLD:
            fails += 1
            with mirror_lock:
                mirror_state["primary_alive"] = False
            logger.warning(f"[Mirror] ⚠️ Missed heartbeat ({fails}/{FAIL_THRESHOLD})")
        else:
            fails = 0
            with mirror_lock:
                mirror_state["primary_alive"] = True

        # Takeover trigger
        if fails >= FAIL_THRESHOLD and not takeover:
            logger.warning("[Mirror] 🚨 Primary unresponsive - initiating takeover.")
            with mirror_lock:
                mirror_state["takeover"] = True
            sup.start_all()

        # Recovery detection (primary back)
        if takeover and delta < HEARTBEAT_INTERVAL * 2:
            logger.info("[Mirror] 🌅 Primary restored - yielding control.")
            sup.stop_all()
            with mirror_lock:
                mirror_state["takeover"] = False
                mirror_state["primary_alive"] = True
            fails = 0

def run_mirror():
    threading.Thread(target=mirror_loop, daemon=True).start()
    # Ensure Flask doesn't spawn a reloader copy (avoid double-start)
    app.run(host="0.0.0.0", port=MIRROR_PORT, debug=False, use_reloader=False, threaded=True)

# ────────────────────────────────────────────────
# Main Entry
# ────────────────────────────────────────────────
def main():
    parser = ArgumentParser()
    parser.add_argument("--role", choices=["primary", "mirror"], default="primary")
    args = parser.parse_args()

    role = args.role.lower()
    logger.info(f"🚀 Launching AION Dual Heartbeat as {role.upper()}")

    if role == "primary":
        primary_loop()
    else:
        run_mirror()

if __name__ == "__main__":
    main()

"""
Deployment Notes
───────────────────────────────────────────────
Env toggles (helpful for dev / Codespaces):
  - AION_ENABLE_FABRIC_SUITE=0          # run heartbeat without spawning the 4 Fabric services
  - AION_HEARTBEAT_INTERVAL=10          # slow down pings
  - AION_HEART_FAIL_THRESHOLD=3         # takeover sensitivity
  - AION_HEART_TOKEN=...                # require Bearer token on /heartbeat/state
  - AION_PYTHON_BIN=/usr/bin/python3    # force interpreter used for child services
"""