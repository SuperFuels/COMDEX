import requests
from typing import List, Dict, Optional, Tuple, Any
from backend.modules.symbolnet.symbolnet_utils import clean_label, score_entity_alignment

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

class WikidataAdapter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "COMDEXSymbolNetBot/1.0 (contact: dev@comdex.ai)"
        })

    def search_entities(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search Wikidata for matching entities (Q-nodes).
        """
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "search": query,
            "limit": limit
        }
        try:
            response = self.session.get(WIKIDATA_API_URL, params=params)
            response.raise_for_status()
            results = response.json().get("search", [])
            return results
        except Exception as e:
            print(f"❌ Wikidata search failed: {e}")
            return []

    def get_entity_summary(self, qid: str) -> Optional[str]:
        """
        Get entity summary/description for a Q-node.
        """
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": qid,
            "props": "descriptions"
        }
        try:
            response = self.session.get(WIKIDATA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            desc = data["entities"][qid]["descriptions"].get("en", {}).get("value", "")
            return desc
        except Exception as e:
            print(f"⚠️ Failed to get description for {qid}: {e}")
            return None

    def fetch_properties(self, qid: str) -> List[Tuple[str, str]]:
        """
        Fetch key property relationships (P-nodes and targets).
        Returns a list of (property_label, value_label).
        """
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            entity_data = response.json()["entities"][qid]

            claims = entity_data.get("claims", {})
            label_cache = {}
            pairs = []

            for prop_id, entries in claims.items():
                for entry in entries:
                    mainsnak = entry.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})
                    value = datavalue.get("value", {})
                    if isinstance(value, dict) and "id" in value:
                        target_id = value["id"]
                        prop_label = self.fetch_label(prop_id, label_cache)
                        target_label = self.fetch_label(target_id, label_cache)
                        if prop_label and target_label:
                            pairs.append((prop_label, target_label))
            return pairs
        except Exception as e:
            print(f"❌ Failed to fetch properties for {qid}: {e}")
            return []

    def fetch_label(self, entity_id: str, cache: Dict[str, str]) -> Optional[str]:
        """
        Fetch and cache label for a Q-node or P-node.
        """
        if entity_id in cache:
            return cache[entity_id]
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": entity_id,
            "props": "labels",
            "languages": "en"
        }
        try:
            response = self.session.get(WIKIDATA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            label = data["entities"][entity_id]["labels"]["en"]["value"]
            cache[entity_id] = label
            return label
        except Exception as e:
            print(f"⚠️ Failed to fetch label for {entity_id}: {e}")
            return None

    def enrich_glyph(self, glyph_text: str) -> Dict[str, Any]:
        """
        Given a glyph (e.g. symbolic term), fetch top Wikidata match and properties.
        """
        cleaned = clean_label(glyph_text)
        matches = self.search_entities(cleaned)

        if not matches:
            return {"glyph": glyph_text, "wikidata": None}

        top = matches[0]
        qid = top.get("id")
        label = top.get("label")
        description = self.get_entity_summary(qid)
        relations = self.fetch_properties(qid)

        score = score_entity_alignment(glyph_text, label, description)

        return {
            "glyph": glyph_text,
            "wikidata": {
                "qid": qid,
                "label": label,
                "description": description,
                "relations": relations,
                "alignment_score": score,
            }
        }

    enrich = enrich_glyph

    def enrich(self, glyph_obj: Any) -> Dict[str, Any]:
        """
        🔌 Required by SymbolNetIngestor.
        Accepts LogicGlyph or EncodedGlyph-like object, calls `enrich_glyph`.
        """
        text = getattr(glyph_obj, "label", None) or getattr(glyph_obj, "symbol", None) or str(glyph_obj)
        return self.enrich_glyph(text)


# ✅ NEW FUNCTION: Top-level SymbolNet-compatible interface
def query_wikidata(label: str, context: str = "", mode: str = "default") -> List[Dict[str, Any]]:
    """
    SymbolNet-compatible query function that wraps WikidataAdapter.
    Returns list of semantic nodes for expansion.
    """
    adapter = WikidataAdapter()
    enriched = adapter.enrich_glyph(label)

    data = enriched.get("wikidata")
    if not data:
        return []

    results = [
        {
            "id": f"wikidata:{data['qid']}",
            "label": data["label"],
            "description": data["description"],
            "type": "entity",
            "source": "wikidata",
            "score": data.get("alignment_score", 0.5)
        }
    ]

    # Optionally add relation triples as extra results
    for prop, value in data.get("relations", []):
        results.append({
            "id": f"wikidata:{data['qid']}:{prop}->{value}",
            "label": f"{prop}: {value}",
            "description": f"Related property of {data['label']}",
            "type": "relation",
            "source": "wikidata",
            "score": 0.4
        })

    return results