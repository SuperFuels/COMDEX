# 📁 backend/tools/generate_reserved_manifest.py
"""
Generates the unified reserved glyph/operator manifest.
───────────────────────────────────────────────
Scans parser modules and PhotonLang grammar to extract:
  * symbolic operators
  * reserved keywords
  * glyph identifiers
Outputs -> backend/modules/photonlang/photon_reserved_map.json
"""

import json, re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "modules/photonlang/photon_reserved_map.json"

# --- Sources ---
GRAMMAR_FILE = ROOT / "modules/photonlang/photonlang_grammar.txt"  # optional rename if needed
QLANG_PARSER = ROOT / "quant/qlang/qlang_parser.py"
SYMATICS_PARSER = ROOT / "codexcore_virtual/instruction_parser.py"
PHOTON_PARSER = ROOT / "modules/photon/photon_parser.py"
LEAN_PARSER = ROOT / "modules/lean/lean_parser.py"

manifest = {
    "ops": {},
    "keywords": {},
    "glyphs": [],
    "domains": [],
}

def extract_ops_from_text(text: str) -> list[str]:
    return sorted(set(re.findall(r"[⊕⊖⊗↔⟲∇μπ->≈⧖✦->]", text)))

def extract_keywords_from_text(text: str) -> list[str]:
    kw = re.findall(r"\"(import|from|wormhole|send|through|save|as|theorem|lemma|def|axiom|constant)\"", text)
    return sorted(set(kw))

# --- Gather from sources ---
text_blobs = {}
for src in [GRAMMAR_FILE, QLANG_PARSER, SYMATICS_PARSER, PHOTON_PARSER, LEAN_PARSER]:
    if src.exists():
        text_blobs[src.name] = src.read_text(encoding="utf-8")

# --- Extract Operators ---
manifest["ops"]["photonlang"] = extract_ops_from_text(text_blobs.get(GRAMMAR_FILE.name, ""))
manifest["ops"]["quantum"] = extract_ops_from_text(text_blobs.get(QLANG_PARSER.name, ""))
manifest["ops"]["symatics"] = extract_ops_from_text(text_blobs.get(SYMATICS_PARSER.name, ""))
manifest["ops"]["photon"] = extract_ops_from_text(text_blobs.get(PHOTON_PARSER.name, ""))
manifest["ops"]["proof"] = extract_ops_from_text(text_blobs.get(LEAN_PARSER.name, ""))

# --- Extract Keywords ---
for name, text in text_blobs.items():
    kws = extract_keywords_from_text(text)
    if kws:
        domain = name.split("_")[0]
        manifest["keywords"][domain] = kws

# --- Domains ---
manifest["domains"] = sorted(manifest["ops"].keys())

# --- Glyphs ---
manifest["glyphs"] = ["💡","🌊","🧠","⚛","✦","🜁","🧭","ψ","Φ","φ","Ψ","μπ"]

# --- Save JSON ---
MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"✅ Reserved manifest generated -> {MANIFEST_PATH}")