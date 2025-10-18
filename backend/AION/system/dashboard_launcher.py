"""
AION Resonant Dashboard Launcher
────────────────────────────────────────────
Integrates the Resonant Ledger Dashboard into the Tessaris / AION control suite.
Supports flexible port selection and automatic process management.

Usage:
    PYTHONPATH=. python backend/AION/system/dashboard_launcher.py
    PYTHONPATH=. python backend/AION/system/dashboard_launcher.py --port 8051
────────────────────────────────────────────
"""

import os
import subprocess
import sys
import time
import logging
import argparse
import socket

DASHBOARD_PATH = "backend/AION/system/network_sync/dashboard.py"

# ───────────────────────────────────────────────
# Logging
# ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AION.DashboardLauncher")


# ───────────────────────────────────────────────
# Validation Helpers
# ───────────────────────────────────────────────
def ensure_dashboard_exists():
    if not os.path.exists(DASHBOARD_PATH):
        logger.error(f"❌ Dashboard not found: {DASHBOARD_PATH}")
        sys.exit(1)
    logger.info(f"✅ Found Resonant Dashboard at: {DASHBOARD_PATH}")


def ensure_port_available(port: int):
    """Check if the given port is free to use."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        logger.warning(f"⚠️ Port {port} already in use. Dashboard may already be running.")
        return False


# ───────────────────────────────────────────────
# Launcher
# ───────────────────────────────────────────────
def launch_dashboard(port: int):
    ensure_dashboard_exists()
    ensure_port_available(port)

    logger.info(f"🚀 Launching Resonant Ledger Dashboard on port {port} ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["DASH_PORT"] = str(port)

    proc = subprocess.Popen(
        [sys.executable, DASHBOARD_PATH],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    logger.info(f"📡 Dashboard running on http://127.0.0.1:{port}")
    logger.info("🪶 Logs will stream below:\n────────────────────────────")

    try:
        for line in proc.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        logger.info("🧩 Stopping dashboard...")
        proc.terminate()
        time.sleep(1)
        sys.exit(0)


# ───────────────────────────────────────────────
# CLI Entrypoint
# ───────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8050, help="Port for dashboard (default=8050)")
    args = parser.parse_args()
    launch_dashboard(args.port)