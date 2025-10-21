# ================================================================
# Tessaris Phase 28: Symatic Inference Network (SIN)
# ================================================================

import asyncio
import json
import websockets
import numpy as np
import networkx as nx
from datetime import datetime
from collections import deque

print("🧩 Starting Tessaris Symatic Inference Network (SIN)…")

# -----------------------------
# Configuration
# -----------------------------
RAL_WS = "ws://localhost:8002/ws/analytics"
BUFFER_SIZE = 256
GRAPH_SAVE_PATH = "backend/data/sin_knowledge.graphml"

buffer = deque(maxlen=BUFFER_SIZE)
G = nx.DiGraph()

# -----------------------------
# Pattern Extraction
# -----------------------------
def extract_motif(packet):
    """Convert incoming analytics packet into symbolic motif tuple."""
    return (
        round(packet.get("nu_mean", 0.0), 3),
        round(packet.get("phi_mean", 0.0), 3),
        round(packet.get("amp_mean", 0.0), 3),
        round(packet.get("drift_entropy", 0.0), 3),
        packet.get("glyph", "•"),
    )

def update_graph(motif):
    """Maintain and evolve the inference graph."""
    global G
    ν, φ, A, H, g = motif
    node_id = f"{g}_{ν}_{φ}_{A:.3f}"

    if node_id not in G:
        G.add_node(node_id, nu=ν, phi=φ, amp=A, entropy=H, glyph=g, ts=datetime.utcnow().isoformat())

    if len(buffer) > 1:
        prev = buffer[-2]
        prev_id = f"{prev[4]}_{prev[0]}_{prev[1]}_{prev[2]:.3f}"
        if prev_id in G:
            G.add_edge(prev_id, node_id, weight=max(1.0 - abs(H - prev[3]), 0.01))

    if len(G) % 25 == 0:
        nx.write_graphml(G, GRAPH_SAVE_PATH)
        print(f"🧠 Updated SIN graph — {len(G.nodes())} nodes, {len(G.edges())} edges")

# -----------------------------
# WebSocket Listener
# -----------------------------
async def listen_ral():
    while True:
        try:
            async with websockets.connect(RAL_WS) as ws:
                print(f"🔗 Connected to RAL analytics stream ({RAL_WS})")
                async for message in ws:
                    packet = json.loads(message)
                    motif = extract_motif(packet)
                    buffer.append(motif)
                    update_graph(motif)
        except Exception as e:
            print(f"⚠️ RAL connection error: {e}, retrying in 5 s…")
            await asyncio.sleep(5)

# -----------------------------
# Inference Loop
# -----------------------------
async def infer_loop():
    while True:
        await asyncio.sleep(10)
        if len(G.nodes()) > 3:
            # Example rule: infer glyph transitions
            last_edges = list(G.edges())[-5:]
            for u, v in last_edges:
                gu = G.nodes[u]["glyph"]
                gv = G.nodes[v]["glyph"]
                rule = f"({gu} → {gv})"
                print(f"🔍 Derived rule: {rule}")

# -----------------------------
# Run both tasks concurrently
# -----------------------------
async def main():
    await asyncio.gather(listen_ral(), infer_loop())

if __name__ == "__main__":
    asyncio.run(main())