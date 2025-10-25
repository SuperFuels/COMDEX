"""
🔄 Photon Converter Tools
-------------------------
Handles conversion between .wiki.phn, .ptn, and JSON representations.
"""

import json
from pathlib import Path
from backend.modules.wiki_capsules.photon_page.photon_page_spec import PhotonPage

def page_to_json(page: PhotonPage) -> str:
    return json.dumps(page.to_dict(), indent=2, ensure_ascii=False)

def json_to_page(data: dict) -> PhotonPage:
    return PhotonPage(
        name=data["name"],
        imports=data.get("imports", []),
        body=data.get("body", ""),
        metadata=data.get("metadata", {})
    )

def save_page(page: PhotonPage, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = page_to_json(page)
    out_path.write_text(content, encoding="utf-8")
    print(f"[PhotonPage] Saved → {out_path}")

def load_page(json_path: Path) -> PhotonPage:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return json_to_page(data)

def wiki_to_page(wiki_data: dict, name: str) -> PhotonPage:
    """Convert Wiki capsule dict → Photon Page scaffold."""
    body = "\n".join(wiki_data.get("definitions", []))
    imports = [wiki_data.get("lemma")]
    meta = wiki_data.get("metadata", {})
    return PhotonPage(name=name, imports=imports, body=body, metadata=meta)