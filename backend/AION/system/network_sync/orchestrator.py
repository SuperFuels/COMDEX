"""
AION Resonant Network Synchronization Layer (v0.3)
────────────────────────────────────────────
Maintains coherence between AION, QQC, Photon, and RQC nodes by exchanging
periodic ψ-κ-T-Φ packets (Resonant Sync Packets).

Each node:
  * Sends sync packets every SYNC_INTERVAL seconds
  * Receives packets via /sync/update endpoint
  * Logs Δφ (phase drift) and Δσ (stability deviation)
  * Writes state deltas into MorphicLedger (if available)

Usage:
    PYTHONPATH=. python backend/AION/system/network_sync/orchestrator.py --node AION_CORE --role primary --port 7090

────────────────────────────────────────────
Configuration Notes
────────────────────────────────────────────
* By default, PEER_HOSTS are read from `backend/config/network_nodes.json`
  to support flexible multi-node setups.
* If that file doesn't exist, it falls back to the static local demo list.
* Each node should list *other* peers - not itself.
────────────────────────────────────────────
"""
import os
import sys
import json
import time
import threading
import logging
import requests
import random
import hashlib
import math
from argparse import ArgumentParser
from flask import Flask, request, jsonify
from logging.handlers import RotatingFileHandler
from backend.AION.fabric.morphic_ingest_bridge import ingest_sync_packet

# ───────────────────────────────────────────────
# Configurable parameters
# ───────────────────────────────────────────────
SYNC_INTERVAL = 3.0           # seconds between sync packets
PHASE_THRESHOLD = 0.05        # max Δφ deviation before corrective event
STATE_FILE = "backend/logs/resonance_sync_state.json"

# ───────────────────────────────────────────────
# Dynamic Peer Discovery
# ───────────────────────────────────────────────
PEER_CONFIG_PATH = "backend/config/network_nodes.json"
if os.path.exists(PEER_CONFIG_PATH):
    try:
        with open(PEER_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            PEER_HOSTS = config.get("peers", [])
            SYNC_PORT = config.get("port", 7090)
            logging.info(f"🔗 Loaded {len(PEER_HOSTS)} peers from network_nodes.json")
    except Exception as e:
        logging.warning(f"⚠️ Failed to load {PEER_CONFIG_PATH}: {e}")
        PEER_HOSTS = ["http://127.0.0.1:7091"]
        SYNC_PORT = 7090
else:
    PEER_HOSTS = ["http://127.0.0.1:7091"]
    SYNC_PORT = 7090

# ───────────────────────────────────────────────
# Shared Sync Token (simple symmetric auth)
# ───────────────────────────────────────────────
SYNC_TOKEN = os.getenv("SYNC_TOKEN", "Resonance_2025")

# ───────────────────────────────────────────────
# Logging setup
# ───────────────────────────────────────────────
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
logger = logging.getLogger("ResonanceSync")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)
file_handler = RotatingFileHandler(STATE_FILE.replace(".json", ".log"), maxBytes=2_000_000, backupCount=2)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ───────────────────────────────────────────────
# MorphicLedger Integration
# ───────────────────────────────────────────────
try:
    from backend.modules.holograms.morphic_ledger import morphic_ledger
    LEDGER_ENABLED = True
    logger.info("📘 MorphicLedger integration active.")
except Exception as e:
    LEDGER_ENABLED = False
    logger.warning(f"⚠️ MorphicLedger unavailable: {e}")

# ───────────────────────────────────────────────
# Node Registry
# ───────────────────────────────────────────────
class NodeRegistry:
    """Tracks all nodes and their ψ-κ-Φ metrics."""
    def __init__(self):
        self.nodes = {}
        self.lock = threading.Lock()
        self.last_phi = {}

    def update(self, packet):
        with self.lock:
            nid = packet["node_id"]
            now = time.time()
            phi = packet.get("phi", 0.0)
            psi = packet.get("psi", 0.0)

            prev_phi = self.last_phi.get(nid, phi)
            Δφ = abs(phi - prev_phi)
            Δσ = abs(psi - 0.8)  # placeholder stability deviation

            self.last_phi[nid] = phi
            self.nodes[nid] = {
                "last_seen": now,
                "metrics": {
                    "psi": psi,
                    "kappa": packet.get("kappa", 0.0),
                    "T": packet.get("T", 0.0),
                    "phi": phi,
                    "Δφ": Δφ,
                    "Δσ": Δσ,
                },
                "role": packet.get("role", "unknown"),
            }

            if LEDGER_ENABLED:
                morphic_ledger.append(
                    {
                        "node": nid,
                        "phi": phi,
                        "delta_phi": Δφ,
                        "sigma": Δσ,
                        "timestamp": now,
                    },
                    observer=nid,
                )

            if Δφ > PHASE_THRESHOLD:
                logger.warning(f"[⚠️] Δφ drift for {nid} exceeds threshold ({Δφ:.3f})")

    def summary(self):
        now = time.time()
        with self.lock:
            return {
                n: {
                    "age": round(now - d["last_seen"], 2),
                    "role": d["role"],
                    **d["metrics"],
                }
                for n, d in self.nodes.items()
            }

registry = NodeRegistry()

# ───────────────────────────────────────────────
# Flask Receiver
# ───────────────────────────────────────────────
app = Flask(__name__)

@app.route("/")
def root():
    """Root status endpoint."""
    return jsonify({
        "status": "ok",
        "node_count": len(registry.nodes),
        "peers": PEER_HOSTS,
        "endpoints": ["/sync/update", "/sync/state"]
    }), 200

@app.route("/sync/update", methods=["POST"])
def sync_update():
    """Receive sync packets from peers."""
    try:
        data = request.get_json(force=True)
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != SYNC_TOKEN:
            return jsonify({"status": "unauthorized"}), 403

        registry.update(data)
        ingest_sync_packet(data)
        write_state_to_file()
        logger.info(f"[<-] Sync update from {data['node_id']} φ={data['phi']:.3f}")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.warning(f"[Receiver] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/sync/state", methods=["GET"])
def sync_state():
    """Return all known nodes and sync info."""
    return jsonify(registry.summary()), 200

# ───────────────────────────────────────────────
# Packet Construction + Broadcast
# ───────────────────────────────────────────────
def generate_local_metrics():
    """Simulate live ψ-κ-T-Φ values for demo (or pull from MorphicLedger)."""
    base = time.time() % 60 / 60  # oscillating base phase
    return {
        "psi": 0.8 + 0.05 * random.uniform(-1, 1),
        "kappa": 0.75 + 0.05 * random.uniform(-1, 1),
        "T": 1.0 + 0.02 * random.uniform(-1, 1),
        "phi": base + 0.02 * random.uniform(-1, 1),
    }

def build_packet(node_id: str, role: str):
    metrics = generate_local_metrics()
    payload = {
        "node_id": node_id,
        "role": role,
        "timestamp": time.time(),
        "uptime": time.perf_counter(),
        **metrics,
    }
    sig = hashlib.sha256((SYNC_TOKEN + node_id).encode()).hexdigest()[:16]
    payload["signature"] = sig
    return payload

def broadcast_loop(node_id: str, role: str):
    """Send sync packets periodically to all peers."""
    while True:
        packet = build_packet(node_id, role)
        for host in PEER_HOSTS:
            try:
                r = requests.post(
                    f"{host}/sync/update",
                    json=packet,
                    headers={"Authorization": f"Bearer {SYNC_TOKEN}"},
                    timeout=2,
                )
                if r.status_code == 200:
                    logger.info(f"[->] Sent sync to {host} φ={packet['phi']:.3f}")
            except Exception as e:
                logger.warning(f"[Broadcast] Failed to reach {host}: {e}")
        registry.update(packet)
        ingest_sync_packet(packet)
        write_state_to_file()
        time.sleep(SYNC_INTERVAL)

# ───────────────────────────────────────────────
# Persistence
# ───────────────────────────────────────────────
def write_state_to_file():
    """Persist live node state for dashboard or visualization."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(registry.summary(), f, indent=2)
        prune_state_file()  # ✅ move this here - run after successful write
    except Exception as e:
        logger.warning(f"Failed to write state file: {e}")

MAX_STATE_ENTRIES = 500  # keep most recent 500 entries

def prune_state_file():
    """Trim resonance_sync_state.json to the most recent MAX_STATE_ENTRIES entries."""
    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()
            # handle multi-json concatenation
            if "}\n{" in data:
                data = "[" + data.replace("}\n{", "},{") + "]"
            parsed = json.loads(data)
            # if dict, skip (it's a snapshot, not a list)
            if isinstance(parsed, dict):
                return
            if len(parsed) > MAX_STATE_ENTRIES:
                trimmed = parsed[-MAX_STATE_ENTRIES:]
                with open(STATE_FILE, "w", encoding="utf-8") as wf:
                    json.dump(trimmed, wf, indent=2)
                logger.info(f"🧹 Pruned state file -> kept {len(trimmed)} entries.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to prune state file: {e}")

# ───────────────────────────────────────────────
# Main entrypoint
# ───────────────────────────────────────────────
def main():
    parser = ArgumentParser()
    parser.add_argument("--node", default="AION_CORE")
    parser.add_argument("--role", default="primary")
    parser.add_argument("--port", type=int, default=SYNC_PORT)
    args = parser.parse_args()

    node_id = args.node
    role = args.role
    port = args.port

    logger.info(f"🌐 Starting Resonant Sync Node [{node_id}] role={role} port={port}")

    # Start broadcaster
    threading.Thread(target=broadcast_loop, args=(node_id, role), daemon=True).start()

    # Start Flask receiver
    app.run(host="0.0.0.0", port=port, threaded=True)

if __name__ == "__main__":
    main()