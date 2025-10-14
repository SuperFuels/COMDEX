"""
🌌 Entanglement Engine — SRK-13 Upgrade
Computes entanglement potentials Φ(a↔b), coherence C, and records
entropy drift ΔS into the Photon Memory Grid (PMG).
"""

import json, time, uuid
import networkx as nx
from math import exp
from typing import Dict, Any

from backend.modules.glyphwave.core.wave_state_store import WaveStateStore
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event
from backend.modules.photon.memory.photon_memory_grid import PhotonMemoryGrid
from backend.modules.glyphwave.decoherence.decoherence_tracker import DecoherenceTracker


class EntanglementEngine:
    def __init__(self):
        self.graph = nx.Graph()
        self.store = WaveStateStore()
        self.pmg = PhotonMemoryGrid()
        self.decoherence = DecoherenceTracker()

    # ───────────────────────────────────────────────
    def entangle(self, wave_a: Dict[str, Any], wave_b: Dict[str, Any]) -> str:
        """Register entanglement between two wave-states with SRK-13 physics."""
        eid = f"E-{uuid.uuid4().hex[:10]}"

        # Compute entanglement physics
        phi_a = wave_a.get("field_potential", 1.0)
        phi_b = wave_b.get("field_potential", 1.0)
        delta_s = abs(phi_a - phi_b) * 0.01
        phi_link = phi_a + phi_b - delta_s

        c_in = (wave_a.get("coherence", 1.0) + wave_b.get("coherence", 1.0)) / 2
        delta_nabla = 1 - exp(-abs(delta_s))
        c_out = round(c_in * (1 - delta_nabla), 5)

        # Graph + PMG registration
        self.graph.add_edge(
            wave_a["id"], wave_b["id"],
            entanglement_id=eid,
            field_potential=phi_link,
            coherence=c_out,
            entropy_shift=delta_s,
            timestamp=time.time()
        )
        self.store.save_entanglement(wave_a, wave_b, eid)
        self.pmg.store_entanglement_state(eid, {
            "phi_link": phi_link,
            "coherence": c_out,
            "entropy_shift": delta_s,
            "timestamp": time.time()
        })
        self.decoherence.track(eid, c_out)

        log_soullaw_event({"type": "entangle", "eid": eid, "coherence": c_out}, glyph=None)
        return eid

    # ───────────────────────────────────────────────
    def collapse_all(self) -> Dict[str, Any]:
        """
        SRK-15 — Collapse all entangled pairs and archive them into PhotonMemoryGrid.
        Each collapsed entanglement is logged with coherence loss and SQI drift.
        """
        start = time.time()
        total_edges = list(self.graph.edges(data=True))
        collapsed_count = 0

        for u, v, data in total_edges:
            eid = data.get("entanglement_id", f"UNK-{uuid.uuid4().hex[:6]}")
            coherence_loss = abs(hash(u) - hash(v)) % 0.01  # simulated delta
            sqi_drift = abs(hash(eid)) % 0.001  # simulated small drift
            try:
                # archive to PMG decay ledger before removal
                if hasattr(self, "pmg"):
                    self.pmg.archive_collapse_event(eid, coherence_loss, sqi_drift)
                collapsed_count += 1
            except Exception as e:
                print(f"[EntanglementEngine] ⚠️ Archive failed for {eid}: {e}")

        self.graph.clear()
        duration = round(time.time() - start, 6)
        metrics = {"collapsed_edges": collapsed_count, "duration_s": duration}

        log_soullaw_event({"type": "collapse_all", **metrics}, glyph=None)
        return metrics

    # ───────────────────────────────────────────────
    def export_graph(self) -> str:
        """Return current entanglement graph as JSON."""
        return json.dumps(nx.readwrite.json_graph.node_link_data(self.graph), indent=2)