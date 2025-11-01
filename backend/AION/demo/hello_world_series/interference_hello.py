"""
🌊 Interference Hello - Superposition Demo
Simulates two coherent oscillators (ψ1, ψ2) combining via ⊕ superposition.
Each iteration computes resultant intensity |ψ1 + ψ2|2 and sends to AION_SYNC node.
"""

import math, time, random, requests, json

SYNC_URL = "http://127.0.0.1:7090/sync/update"
SYNC_TOKEN = "Resonance_2025"

def interference_pattern(phi1, phi2):
    """Compute normalized interference intensity."""
    return 0.5 * (1 + math.cos(2 * math.pi * (phi1 - phi2)))

def main():
    print("🌊 Running Interference Hello (⊕ superposition) ...")
    for i in range(20):
        phi1 = random.random()
        phi2 = random.random()
        I = interference_pattern(phi1, phi2)

        payload = {
            "node_id": "INTERFERENCE_HELLO",
            "role": "demo",
            "psi": I,
            "phi": phi1,
            "phi_ref": phi2,
            "intensity": I,
            "timestamp": time.time(),
        }

        r = requests.post(SYNC_URL, json=payload, headers={"Authorization": f"Bearer {SYNC_TOKEN}"})
        print(f"⊕ sent interference φ1={phi1:.3f}, φ2={phi2:.3f}, I={I:.3f}, status={r.status_code}")
        time.sleep(1.5)

if __name__ == "__main__":
    main()