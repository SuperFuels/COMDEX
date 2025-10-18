"""
🧠 AION Hello — End-to-End Cognitive Feedback Demo
Simulates AION emitting coherent ψ κ T Φ resonance packets to MorphicLedger → CodexTrace.
"""

import time, random, requests, json, hashlib

MORPHIC_FEED = "backend/logs/morphic_ingest_backup.jsonl"
SYNC_URL = "http://127.0.0.1:7090/sync/update"
SYNC_TOKEN = "Resonance_2025"

def gen_metrics():
    return {
        "psi": 0.8 + 0.1 * random.uniform(-1, 1),
        "kappa": 0.75 + 0.1 * random.uniform(-1, 1),
        "T": 1.0 + 0.05 * random.uniform(-1, 1),
        "phi": random.random(),
    }

def main():
    print("🧠 Running AION Hello (ψ κ T Φ → Morphic → CodexTrace) …")
    for i in range(15):
        metrics = gen_metrics()
        packet = {
            "timestamp": time.time(),
            "node_id": "AION_HELLO",
            "role": "primary",
            "metrics": metrics,
            "signature": hashlib.sha256((SYNC_TOKEN + str(i)).encode()).hexdigest()[:16],
        }

        # Append to Morphic feed
        with open(MORPHIC_FEED, "a", encoding="utf-8") as f:
            f.write(json.dumps(packet) + "\n")

        # Send to Resonant Sync
        r = requests.post(SYNC_URL, json=packet, headers={"Authorization": f"Bearer {SYNC_TOKEN}"})
        print(f"→ sent AION_HELLO ψ={metrics['psi']:.3f}, φ={metrics['phi']:.3f}, status={r.status_code}")
        time.sleep(2)

if __name__ == "__main__":
    main()