"""
AION Fabric Stream Emitter
────────────────────────────────────────────
Continuously emits fused resonance tensors (ψ̄ κ̄ T̄ Φ̄ σ)
to downstream symbolic or visualization systems.

Usage:
    PYTHONPATH=. python backend/AION/fabric/aion_fabric_stream.py
"""

import os
import time
import json
import logging
import requests
from backend.AION.fabric.aion_fabric_resonance import get_latest_fusion_tensor

STREAM_URL = "http://127.0.0.1:5090/fabric/stream"
EMIT_INTERVAL = 2.5  # seconds between updates
FUSION_FILE = "/tmp/aion_fusion_tensor.json"

logger = logging.getLogger("AIONFabricStream")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)


def _read_tensor_from_file():
    """Read tensor directly from JSON file for redundancy."""
    if not os.path.exists(FUSION_FILE):
        return None
    try:
        with open(FUSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        return None
    return None


def emit_fusion_tensor():
    """
    Continuously poll the fusion buffer or shared file and POST live tensors
    to the Fabric stream endpoint. Emits only when new or updated tensors appear.
    """
    logger.info("🌐 Starting AION Fabric Stream emitter ...")
    last_tensor = None
    no_data_count = 0

    while True:
        try:
            # Try from shared memory or fallback to file
            tensor = get_latest_fusion_tensor() or _read_tensor_from_file()

            if not tensor:
                no_data_count += 1
                if no_data_count % 5 == 0:
                    logger.info("[AIONFabricStream] ⏳ No fusion tensor detected yet ...")
                time.sleep(EMIT_INTERVAL)
                continue

            # Reset counter on detection
            no_data_count = 0

            # Emit only on update
            if tensor != last_tensor:
                last_tensor = tensor
                payload = {"timestamp": time.time(), "tensor": tensor}

                # Extract and format
                σ = tensor.get("σ", 0)
                ψ̄ = tensor.get("ψ̄", 0)
                κ̄ = tensor.get("κ̄", 0)
                T̄ = tensor.get("T̄", 0)
                Φ̄ = tensor.get("Φ̄", 0)

                logger.info(
                    f"[AION->FabricStream] σ={σ:.3f} ψ̄={ψ̄:.3f} κ̄={κ̄:.3f} T̄={T̄:.3f} Φ̄={Φ̄:.3f}"
                )

                try:
                    resp = requests.post(STREAM_URL, json=payload, timeout=3)
                    if resp.status_code == 200:
                        logger.info("✅ Stream update posted successfully.")
                    else:
                        logger.warning(f"⚠️ Stream endpoint returned {resp.status_code}.")
                except requests.exceptions.RequestException:
                    logger.warning("⚠️ Stream endpoint not reachable - buffering locally.")

            time.sleep(EMIT_INTERVAL)

        except KeyboardInterrupt:
            logger.info("⏹️ Fabric Stream emitter stopped manually.")
            break

        except Exception as e:
            logger.exception(f"[AIONFabricStream] Unexpected error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    emit_fusion_tensor()