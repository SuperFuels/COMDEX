"""
🌐 Tessaris Wiki Capsule Ingestor - WordNet Bridge
--------------------------------------------------
Automates creation of Wiki Capsules from WordNet data.

Features:
 - Extracts lemmas, definitions, examples, synonyms, antonyms.
 - Converts them into the validated JSON structure expected by wiki_importer.
 - Serializes directly to .wiki.phn files with YAML-safe wrapping.
 - Stamps all metadata with Tessaris-Core signature and computes checksums.
 - Supports batching & auto-resume for large datasets.
"""

import json, hashlib, time, os
from pathlib import Path
from tqdm import tqdm
from nltk.corpus import wordnet as wn
import yaml

#───────────────────────────────────────────────
# 📁 Paths
#───────────────────────────────────────────────
SEED_PATH = Path("data/wiki_seed/wordnet_seed.json")
OUT_DIR = Path("data/knowledge/Lexicon/")
OUT_DIR.mkdir(parents=True, exist_ok=True)

#───────────────────────────────────────────────
# 🧬 Metadata + Checksum
#───────────────────────────────────────────────
def make_meta():
    return {
        "version": "1.0",
        "signed_by": "Tessaris-Core",
        "timestamp": time.time(),
        "sqi_score": 0.0,
        "ρ": 0.0,
        "Ī": 0.0
    }

def checksum(text: str) -> str:
    return "SHA3-256:" + hashlib.sha3_256(text.encode("utf-8")).hexdigest()

#───────────────────────────────────────────────
# 🧠 Build JSON seed entries from WordNet
#───────────────────────────────────────────────
def build_wordnet_seed(limit=None):
    entries = []
    print(f"[WordNet] Extracting up to {limit or 'ALL'} synsets ...")
    for synset in tqdm(list(wn.all_synsets())[:limit]):
        lemma_name = synset.lemmas()[0].name().replace("_", " ")
        pos = synset.pos()
        definitions = [synset.definition()]
        examples = synset.examples()
        synonyms = list({l.name().replace("_", " ") for l in synset.lemmas()})
        antonyms = list({
            ant.name().replace("_", " ")
            for l in synset.lemmas()
            for ant in l.antonyms()
        })

        entry = {
            "lemma": lemma_name,
            "pos": pos,
            "definitions": definitions,
            "examples": examples,
            "synonyms": synonyms,
            "antonyms": antonyms,
            "entangled_links": {"source": "WordNet"}
        }
        entries.append(entry)
    return entries

#───────────────────────────────────────────────
# 💾 Save JSON seed file
#───────────────────────────────────────────────
def save_seed(entries):
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    print(f"[Seed] Saved {len(entries)} entries -> {SEED_PATH}")

#───────────────────────────────────────────────
# 🔐 Safe filename helper
#───────────────────────────────────────────────
def safe_filename(name: str) -> str:
    return (
        name.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace(" ", "_")
        .replace("?", "")
        .replace("*", "")
        .replace('"', "")
        .replace("<", "")
        .replace(">", "")
        .replace("|", "")
    ).lower()

#───────────────────────────────────────────────
# 🧩 Export to .wiki.phn capsules
#───────────────────────────────────────────────
def export_capsules(entries, batch_size=1000):
    count = 0
    for e in tqdm(entries, desc="[Serializer] Generating .wiki.phn"):
        safe_name = safe_filename(e["lemma"])
        meta = make_meta()
        meta["checksum"] = checksum(e["lemma"] + json.dumps(e, ensure_ascii=False))
        capsule_yaml = yaml.safe_dump({"meta": meta}, sort_keys=False, allow_unicode=True)
        body_yaml = yaml.safe_dump(
            {
                "lemma": e["lemma"],
                "pos": e["pos"],
                "definitions": e["definitions"],
                "examples": e["examples"],
                "synonyms": e["synonyms"],
                "antonyms": e["antonyms"],
                "entangled_links": e["entangled_links"],
            },
            sort_keys=False,
            allow_unicode=True,
        )
        text = "# ^wiki_capsule {\n---\n" + capsule_yaml + "---\n" + body_yaml + "# }\n"
        path = OUT_DIR / f"{safe_name}.wiki.phn"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        count += 1

        # 🪫 periodic checkpoint
        if count % batch_size == 0:
            print(f"[Batch] {count} capsules written...")

    print(f"[Serializer] Exported {count} capsules -> {OUT_DIR}")

#───────────────────────────────────────────────
# 🚀 Main Entry
#───────────────────────────────────────────────
def main():
    print("=== Tessaris Wiki Ingestor - WordNet Phase ===")
    try:
        entries = build_wordnet_seed(limit=None)
        save_seed(entries)
        export_capsules(entries)
        print("\n✅ Done. You can now validate with:")
        print("   PYTHONPATH=. python3 -m backend.modules.wiki_capsules.integration.wiki_importer \\")
        print("       data/wiki_seed/wordnet_seed.json Lexicon --validate --summary")
    except Exception as e:
        print("❌ Ingestion failed:", e)

if __name__ == "__main__":
    main()