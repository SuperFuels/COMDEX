import os
import csv
import json
import numpy as np
from collections import defaultdict
from nltk.corpus import wordnet as wn
from typing import Dict, List, Tuple, Optional

# Optional: Wikidata loader placeholder
try:
    from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON
except ImportError:
    SPARQLWrapper = None

# ------------------------
# Global Vector Store
# ------------------------
numberbatch_vectors: Dict[str, List[float]] = {}
numberbatch_loaded = False

def load_numberbatch(path: str):
    global numberbatch_vectors, numberbatch_loaded

    if not os.path.exists(path):
        print(f"[SymbolNet] ❌ Numberbatch file not found at {path}. Semantic scoring will be disabled.")
        numberbatch_loaded = False
        return

    print(f"[SymbolNet] 🔢 Loading Numberbatch vectors from {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(' '):
                continue  # Skip headers
            parts = line.strip().split()
            word = parts[0]
            vector = list(map(float, parts[1:]))
            numberbatch_vectors[word] = vector

    numberbatch_loaded = True
    print(f"[SymbolNet] ✅ Loaded {len(numberbatch_vectors)} vectors.")

def cosine_similarity(v1, v2):
    v1, v2 = np.array(v1), np.array(v2)
    if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
        return 0.0
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def get_semantic_vector(label: str) -> Optional[List[float]]:
    if not numberbatch_loaded:
        return None
    key = label.lower().replace(" ", "_")
    return numberbatch_vectors.get(key)


# ------------------------
# SymbolNetLoader Core
# ------------------------
class SymbolNetLoader:
    def __init__(self):
        self.conceptnet_path = "data/conceptnet/conceptnet-assertions.csv"
        self.wordnet_loaded = False
        self.wikidata_loaded = False

        self.symbol_registry = defaultdict(list)  # {symbol_label: [definitions]}
        self.entity_cache = {}  # {id: {label, type, metadata}}

    # -------------------
    # ConceptNet Loading
    # -------------------
    def load_conceptnet(self, max_rows: int = 100000):
        if not os.path.exists(self.conceptnet_path):
            print(f"[SymbolNet] ⚠️ ConceptNet file not found at: {self.conceptnet_path}")
            return

        print(f"[SymbolNet] 📚 Loading ConceptNet from {self.conceptnet_path}")
        with open(self.conceptnet_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t')
            for i, row in enumerate(reader):
                if i == 0 or len(row) < 5:
                    continue
                uri, rel, start, end, meta = row[:5]
                if "/en/" not in start or "/en/" not in end:
                    continue

                source = start.split("/en/")[-1].replace("_", " ")
                target = end.split("/en/")[-1].replace("_", " ")
                rel_type = rel.split("/")[-1]

                self.symbol_registry[source].append({
                    "relation": rel_type,
                    "target": target,
                    "source": source,
                    "source_type": "ConceptNet"
                })

                if i >= max_rows:
                    break

        print(f"[SymbolNet] ✅ Loaded {len(self.symbol_registry)} ConceptNet entries")

    # -------------------
    # WordNet Loading
    # -------------------
    def load_wordnet(self):
        print("[SymbolNet] 📖 Loading WordNet entries...")
        for synset in wn.all_synsets():
            for lemma in synset.lemmas():
                name = lemma.name().replace("_", " ")
                definition = synset.definition()

                self.symbol_registry[name].append({
                    "relation": "definition",
                    "target": definition,
                    "source_type": "WordNet",
                    "pos": synset.pos()
                })

        self.wordnet_loaded = True
        print(f"[SymbolNet] ✅ Loaded {len(self.symbol_registry)} WordNet entries")

    # -------------------
    # Wikidata Loader (stub)
    # -------------------
    def load_wikidata(self, query_limit: int = 100):
        if SPARQLWrapper is None:
            print("[SymbolNet] ⚠️ SPARQLWrapper not installed. Skipping Wikidata.")
            return

        print("[SymbolNet] 🌐 Loading Wikidata concepts via SPARQL...")
        endpoint = SPARQLWrapper("https://query.wikidata.org/sparql")
        endpoint.setQuery(f'''
            SELECT ?item ?itemLabel WHERE {{
              ?item wdt:P31 wd:Q35120.
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }} LIMIT {query_limit}
        ''')
        endpoint.setReturnFormat(SPARQL_JSON)
        results = endpoint.query().convert()

        for result in results["results"]["bindings"]:
            label = result["itemLabel"]["value"]
            uri = result["item"]["value"]

            self.symbol_registry[label].append({
                "relation": "wikidata_uri",
                "target": uri,
                "source_type": "Wikidata"
            })

        self.wikidata_loaded = True
        print(f"[SymbolNet] ✅ Loaded {len(results['results']['bindings'])} Wikidata entries")

    # -------------------
    # Unified Access
    # -------------------
    def get_definitions(self, symbol_label: str) -> List[Dict]:
        return self.symbol_registry.get(symbol_label, [])

    def export_registry(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.symbol_registry, f, indent=2, ensure_ascii=False)
        print(f"[SymbolNet] 💾 Exported symbol registry to {path}")


# Optional CLI loader
if __name__ == "__main__":
    load_numberbatch("data/conceptnet/numberbatch-en-19.08.txt")

    loader = SymbolNetLoader()
    loader.load_conceptnet()
    loader.load_wordnet()
    loader.load_wikidata()
    loader.export_registry("symbol_registry.json")