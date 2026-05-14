"""
🔗 Entangle Hello - AION↔QQC Phase Correlation Demo
Creates two linked nodes (entangled φ states) and propagates correlated updates.
"""

import time, random, requests

AION_URL = "http://127.0.0.1:7090/sync/update"
QQC_URL  = "http://127.0.0.1:7091/sync/update"
SYNC_TOKEN = "Resonance_2025"

def correlated_phase():
    """Generate a base φ and a correlated offset."""
    base = random.random()
    offset = base + random.uniform(-0.02, 0.02)
    return base % 1.0, offset % 1.0

def main():
    print("🔗 Running Entangle Hello (↔ correlation) ...")
    for i in range(20):
        phi_aion, phi_qqc = correlated_phase()
        packet_aion = {"node_id": "AION_ENTANGLE", "role": "entangle", "phi": phi_aion}
        packet_qqc  = {"node_id": "QQC_ENTANGLE",  "role": "entangle", "phi": phi_qqc}

        for url, packet in [(AION_URL, packet_aion), (QQC_URL, packet_qqc)]:
            r = requests.post(url, json=packet, headers={"Authorization": f"Bearer {SYNC_TOKEN}"})
            print(f"↔ sent {packet['node_id']} φ={packet['phi']:.3f}, status={r.status_code}")

        time.sleep(2)

if __name__ == "__main__":
    main()