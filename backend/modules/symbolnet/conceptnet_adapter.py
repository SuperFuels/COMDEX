import requests
from typing import List, Dict, Optional, Union
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

CONCEPTNET_API = "https://api.conceptnet.io"

RELATION_TO_TYPE = {
    "/r/IsA": "is_a",
    "/r/PartOf": "part_of",
    "/r/Causes": "causes",
    "/r/HasProperty": "has_property",
    "/r/UsedFor": "used_for",
    "/r/CapableOf": "capable_of",
    "/r/RelatedTo": "related_to",
}

class ConceptNetAdapter:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.kg_writer = KnowledgeGraphWriter()

    def query_concept(self, term: str, limit: int = 10) -> List[Dict]:
        url = f"{CONCEPTNET_API}/c/{self.lang}/{term}?limit={limit}"
        try:
            resp = requests.get(url)
            data = resp.json()
            return data.get("edges", [])
        except Exception as e:
            print(f"❌ ConceptNet query failed: {e}")
            return []

    def normalize_conceptnet_edge(self, edge: Dict) -> Optional[LogicGlyph]:
        rel = edge.get("rel", {}).get("@id")
        rel_type = RELATION_TO_TYPE.get(rel)
        if not rel_type:
            return None

        start_label = edge.get("start", {}).get("label")
        end_label = edge.get("end", {}).get("label")

        if not start_label or not end_label:
            return None

        return LogicGlyph(
            glyph_type="conceptnet_relation",
            label=rel_type,
            data={
                "start": start_label,
                "end": end_label,
                "source": "ConceptNet",
                "raw_relation": rel,
            },
            metadata={
                "weight": edge.get("weight", 1.0),
                "surfaceText": edge.get("surfaceText"),
            }
        )

    def fetch_and_convert(self, term: str, limit: int = 10) -> List[LogicGlyph]:
        print(f"🔍 [ConceptNetAdapter] Looking up term: {term}")
        edges = self.query_concept(term, limit)
        glyphs = []

        for edge in edges:
            glyph = self.normalize_conceptnet_edge(edge)
            if glyph:
                glyphs.append(glyph)

        return glyphs

    def enrich(self, glyph: Union[LogicGlyph, Dict, str], limit: int = 10) -> List[LogicGlyph]:
        term = self.safe_extract_label(glyph)
        return self.fetch_and_convert(term, limit)

    def inject_to_container(self, term: str, container_id: str, limit: int = 10) -> int:
        glyphs = self.fetch_and_convert(term, limit)
        injected = 0

        for glyph in glyphs:
            self.kg_writer.store_glyph_in_container(container_id, glyph)
            injected += 1

        return injected

    def safe_extract_label(self, glyph: Union[LogicGlyph, Dict, str]) -> str:
        if hasattr(glyph, "label") and callable(glyph.label):
            return glyph.label()
        elif isinstance(glyph, dict):
            return glyph.get("label") or glyph.get("symbol") or str(glyph)
        return str(glyph)

# 🔌 Required by symbolnet_bridge.py
def query_conceptnet(term: str) -> Dict:
    """
    SymbolNet-compatible wrapper to fetch ConceptNet data for a glyph.
    """
    adapter = ConceptNetAdapter()
    glyphs = adapter.fetch_and_convert(term)

    return {
        "source": "conceptnet",
        "term": term,
        "relations": [g.to_dict() for g in glyphs],
        "description": f"ConceptNet relations for '{term}'",
    }