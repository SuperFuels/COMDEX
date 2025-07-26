import copy
from typing import Dict, List, Union
from backend.modules.hologram.ghx_packet_validator import GHXPacketValidator
from backend.modules.codex.collapse_trace_exporter import export_collapse_trace

class HologramIntegrator:
    def __init__(self, ghx_packet: Dict):
        self.ghx = ghx_packet
        self.validator = GHXPacketValidator(self.ghx)

    def embed_into_container(self, base_container: Dict) -> Dict:
        """
        Merges GHX glyphs into a `.dc.json` container and updates metadata.
        """
        valid, errors, _ = self.validator.validate()
        if not valid:
            raise ValueError(f"Invalid GHX packet: {errors}")

        container = copy.deepcopy(base_container)
        container.setdefault("hologram", {})["embedded_ghx"] = self.ghx["ghx_id"]
        container.setdefault("glyphs", []).extend(self.ghx["glyphs"])

        container["meta"] = container.get("meta", {})
        container["meta"]["hologram_embedded"] = True
        container["meta"]["compression_state"] = "expanded"
        container["meta"]["last_updated"] = self.ghx["meta"].get("created_at")

        return container

    def collapse_to_snapshot(self) -> Dict:
        """
        Collapses GHX back into a `.dc`-ready symbolic container snapshot.
        """
        trace = export_collapse_trace(self.ghx)
        snapshot = {
            "container_id": f"collapsed_{self.ghx['ghx_id']}",
            "physics": "symbolic-quantum",
            "glyphs": trace["glyph_sequence"],
            "meta": {
                "compressed_from": self.ghx["ghx_id"],
                "collapse_time": trace["timestamp"],
                "entropy_score": self.ghx["meta"].get("entropy_score"),
                "origin_signature": self.ghx["meta"].get("created_by"),
                "compression_state": "collapsed"
            }
        }
        return snapshot

    def trace_entanglement_links(self) -> List[Dict]:
        """
        Returns a simplified list of all entanglement relationships.
        """
        links = []
        glyphs = self.ghx.get("glyphs", [])
        for g in glyphs:
            for e in g.get("entangled", []):
                links.append({"source": g["id"], "target": e})
        return links