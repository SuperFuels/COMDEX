"""
AION Fabric Stream Receiver
────────────────────────────────────────────
Listens on HTTP endpoint /fabric/stream and receives live resonance tensors
(ψ̄ κ̄ T̄ Φ̄ σ) from the AION Fabric Stream emitter.

The receiver logs, stores, and can forward these tensors to:
  * Morphic Fabric state visualizer
  * CodexTrace dashboards
  * Cognitive coherence monitors

Usage:
    PYTHONPATH=. python backend/AION/fabric/fabric_stream_receiver.py
"""

from flask import Flask, request, jsonify
import logging
import time
import json
import os

app = Flask(__name__)
logger = logging.getLogger("AIONFabricReceiver")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# In-memory history store
_RECEIVED_TENSORS = []
RECEIVED_FILE = "/tmp/aion_fabric_stream_log.json"


@app.route("/fabric/stream", methods=["POST"])
def receive_tensor():
    """Receive a live fusion tensor from the AION Fabric Stream emitter."""
    try:
        data = request.get_json(force=True)
        tensor = data.get("tensor", {})

        ψ̄ = tensor.get("ψ̄")
        κ̄ = tensor.get("κ̄")
        T̄ = tensor.get("T̄")
        Φ̄ = tensor.get("Φ̄")
        σ = tensor.get("σ")

        logger.info(f"[AION<-Stream] σ={σ:.3f} ψ̄={ψ̄:.3f} κ̄={κ̄:.3f} T̄={T̄:.3f} Φ̄={Φ̄:.3f}")

        record = {
            "timestamp": data.get("timestamp", time.time()),
            "tensor": tensor,
        }
        _RECEIVED_TENSORS.append(record)

        # Keep the log short (latest 200 entries)
        if len(_RECEIVED_TENSORS) > 200:
            _RECEIVED_TENSORS.pop(0)

        # Write to file for visualization clients
        with open(RECEIVED_FILE, "w", encoding="utf-8") as f:
            json.dump(_RECEIVED_TENSORS[-50:], f, indent=2)

        return jsonify({"status": "ok", "received": True}), 200

    except Exception as e:
        logger.exception(f"[AIONFabricReceiver] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/fabric/last", methods=["GET"])
def last_tensor():
    """Retrieve the latest fusion tensor (for visualization)."""
    if not _RECEIVED_TENSORS:
        return jsonify({"status": "empty"}), 404
    return jsonify(_RECEIVED_TENSORS[-1]), 200


@app.route("/fabric/all", methods=["GET"])
def all_tensors():
    """Retrieve the recent stream log."""
    return jsonify(_RECEIVED_TENSORS[-50:]), 200


if __name__ == "__main__":
    logger.info("🛰️  Starting AION Fabric Stream Receiver on port 5090 ...")
    app.run(host="0.0.0.0", port=5090)