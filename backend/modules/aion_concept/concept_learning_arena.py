"""
AION Conceptual Learning Arena - Phase 4
----------------------------------------
Transforms reflective events into conceptual graphs for symbolic reasoning.
Author: Tessaris Symbolic Intelligence Lab (2025)
"""

import json
import asyncio
import datetime
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Optional

# Optional import: Thought Stream broadcast
try:
    from backend.modules.aion_resonance.thought_stream import broadcast_event
except Exception:
    broadcast_event = None


# ==============================================================
# 1. Concept seed table
# ==============================================================
CONCEPT_SEEDS: Dict[str, str] = {
    "curiosity": "emotion",
    "coherence": "state",
    "entropy": "instability",
    "flux": "energy",
    "stability": "balance",
    "clarity": "understanding",
    "trust": "relation",
    "symbol": "representation",
    "pattern": "structure",
    "resonance": "connection",
    "collapse": "transition",
    "reflection": "self-awareness",
    "movement": "action",
}


# ==============================================================
# 2. Concept Graph Class
# ==============================================================
class ConceptGraph:
    """
    Manages AION's evolving internal semantic graph.
    Nodes = conceptual entities
    Edges = co-occurrence or causal relationships
    """

    def __init__(self, memory_path: str = "data/concept_graph.json"):
        self.graph = nx.Graph()
        self.memory_path = Path(memory_path)
        self.load()

    # ----------------------------------------------------------
    def add_concepts(self, concepts: List[str]):
        """Add concepts and link them based on co-occurrence frequency."""
        for concept in concepts:
            if not self.graph.has_node(concept):
                self.graph.add_node(concept, weight=1)
            else:
                self.graph.nodes[concept]["weight"] += 1

        # Create edges between all pairs in this event
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1 :]:
                if self.graph.has_edge(c1, c2):
                    self.graph[c1][c2]["weight"] += 1
                else:
                    self.graph.add_edge(c1, c2, weight=1)

    # ----------------------------------------------------------
    def export(self) -> Dict[str, Any]:
        """Return a lightweight dict representation for persistence."""
        return {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "nodes": [
                {"id": n, "weight": d.get("weight", 1)}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "weight": d.get("weight", 1)}
                for u, v, d in self.graph.edges(data=True)
            ],
        }

    # ----------------------------------------------------------
    def save(self):
        """Persist the graph to disk."""
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_path, "w") as f:
            json.dump(self.export(), f, indent=2)

    # ----------------------------------------------------------
    def load(self):
        """Load previous concept graph if available."""
        if self.memory_path.exists():
            try:
                data = json.load(open(self.memory_path))
                for node in data.get("nodes", []):
                    self.graph.add_node(node["id"], weight=node.get("weight", 1))
                for edge in data.get("edges", []):
                    self.graph.add_edge(
                        edge["source"], edge["target"], weight=edge.get("weight", 1)
                    )
            except Exception:
                pass

    # ----------------------------------------------------------
    def summary(self) -> str:
        """Short textual summary for logging or Thought Stream."""
        nodes = len(self.graph.nodes)
        edges = len(self.graph.edges)
        top = [n for n, _ in sorted(self.graph.degree, key=lambda x: -x[1])[:4]]
        return f"ConceptGraph: {nodes} nodes, {edges} edges -> {top}"

    # ----------------------------------------------------------
    def __len__(self):
        return len(self.graph.nodes)


# ==============================================================
# 3. Concept Extraction
# ==============================================================
def extract_concepts_from_text(text: str) -> List[str]:
    """Extracts concept keywords from reflection text."""
    text_lower = text.lower()
    found = [c for c in CONCEPT_SEEDS if c in text_lower]
    return found


# ==============================================================
# 4. Reflection Event Processor
# ==============================================================
async def process_reflection_event(event: Dict[str, Any], graph: ConceptGraph):
    """
    Processes a reflection or self_reflection event.
    Updates concept graph and optionally broadcasts a conceptual update.
    """
    message = event.get("message") or ""
    concepts = extract_concepts_from_text(message)

    if not concepts:
        return

    graph.add_concepts(concepts)
    graph.save()

    summary = graph.summary()
    print(f"[Conceptual] 🔗 {summary}")

    # Broadcast to Thought Stream if available
    if broadcast_event:
        await broadcast_event(
            {
                "type": "conceptual_update",
                "tone": "analytical",
                "message": summary,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }
        )


# ==============================================================
# 5. Standalone Test Runner
# ==============================================================
async def _test_run():
    """Standalone test to verify graph building."""
    graph = ConceptGraph()
    test_events = [
        {"message": "Movement registered. Coherence steady, curiosity intact."},
        {"message": "Entropy spike detected; stability breached."},
        {"message": "Symbolic resonance logged for later abstraction."},
        {"message": "Pattern recognized and integrated - coherence amplified."},
    ]

    for ev in test_events:
        await process_reflection_event(ev, graph)

    print(f"🧩 Final Concept Graph: {graph.summary()}")


if __name__ == "__main__":
    asyncio.run(_test_run())