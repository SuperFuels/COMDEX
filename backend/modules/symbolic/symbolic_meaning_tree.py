# backend/modules/symbolic/symbolic_meaning_tree.py

from typing import List, Dict, Any, Optional

class SymbolicMeaningTree:
    def __init__(self, root_glyph: str, nodes: List[Dict], edges: List[Dict]):
        self.root_glyph = root_glyph
        self.nodes = nodes
        self.edges = edges

    @classmethod
    def from_container(cls, container: dict) -> "SymbolicMeaningTree":
        """
        Generate a symbolic meaning tree from a .dc.json container.
        Uses glyphs and metadata fields to build node/edge structures.
        """
        glyphs = container.get("glyphs", [])
        edges = []
        nodes = []
        root_glyph = None

        for glyph in glyphs:
            gid = glyph.get("id") or glyph.get("label") or f"glyph_{len(nodes)}"
            node = {
                "id": gid,
                "label": glyph.get("label", ""),
                "type": glyph.get("type", ""),
                "metadata": glyph.get("metadata", {}),
            }
            nodes.append(node)

            # Mark root glyph
            if glyph.get("metadata", {}).get("is_root", False):
                root_glyph = gid

            # Auto-link based on parent/child in metadata
            links = glyph.get("metadata", {}).get("links", [])
            for target_id in links:
                edges.append({
                    "source": gid,
                    "target": target_id,
                })

        if not root_glyph and nodes:
            root_glyph = nodes[0]["id"]  # Fallback

        return cls(root_glyph=root_glyph, nodes=nodes, edges=edges)

    @classmethod
    def from_beam(cls, beam: Any) -> "SymbolicMeaningTree":
        """
        Create a SymbolicMeaningTree from a WaveState beam object.
        Extracts minimal structure using beam.glyph_data and ID fields.
        This is used for benchmarks and simplified symbolic traces.
        """
        glyph_id = getattr(beam, "glyph_id", "beam_glyph")
        glyph_data = getattr(beam, "glyph_data", {})

        root_node = {
            "id": glyph_id,
            "label": glyph_data.get("label", glyph_id),
            "type": glyph_data.get("type", "wave"),
            "metadata": glyph_data,
        }

        return cls(
            root_glyph=glyph_id,
            nodes=[root_node],
            edges=[],
        )

    def print_summary(self):
        """
        Pretty-print summary of the tree contents.
        """
        print(f"\n🔎 [bold]Tree Summary:[/bold]")
        for node in self.nodes:
            print(f"• [blue]{node['id']}[/blue] — {node['label']} ({node['type']})")

        print(f"\n🔗 [bold]Connections:[/bold]")
        for edge in self.edges:
            print(f"→ {edge['source']} → {edge['target']}")
