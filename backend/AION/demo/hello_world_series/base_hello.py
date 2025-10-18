# backend/AION/demo/hello_world_series/base_hello.py
import time, requests, json

SYNC_ENDPOINT = "http://127.0.0.1:7090/sync/update"
SYNC_TOKEN = "Resonance_2025"

def send_hello(node_id, role, psi, kappa, T, phi):
    packet = {
        "node_id": node_id,
        "role": role,
        "timestamp": time.time(),
        "psi": psi, "kappa": kappa, "T": T, "phi": phi,
        "deltas": {"dphi": 0.0, "dsigma": 0.0}
    }
    r = requests.post(
        SYNC_ENDPOINT,
        json=packet,
        headers={"Authorization": f"Bearer {SYNC_TOKEN}"},
        timeout=3
    )
    print(f"→ sent {node_id}: φ={phi:.3f}, status={r.status_code}")