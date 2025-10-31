# backend/modules/photonlang/page_runner.py
from __future__ import annotations
import json, os, hashlib, time
from typing import Dict, Any

from backend.modules.photonlang.interpreter import run_source
from backend.modules.photonlang.photon_page_validator import validate_page_entanglement

PTN_DIR = "workspace/pages"
os.makedirs(PTN_DIR, exist_ok=True)

def _hash_lock(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def _entropy_signature(page: Dict[str, Any]) -> float:
    txt = json.dumps(page, sort_keys=True)
    return round(sum(ord(c) for c in txt) / len(txt), 5)

def run_ptn_page(path: str) -> Dict[str, Any]:
    if not path.endswith(".ptn"):
        raise ValueError("PhotonPageRunner requires .ptn file")

    with open(path, "r", encoding="utf-8") as f:
        page = json.load(f)

    validate_page_entanglement(page)

    src = page.get("source", "")
    if not src:
        return {"status": "empty", "path": path}

    result = run_source(src)

    page["last_run"] = time.time()
    page["entropy_signature"] = _entropy_signature(page)
    page["hash_lock"] = _hash_lock(json.dumps(page, sort_keys=True))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(page, f, indent=2, ensure_ascii=False)

    return {
        "status": "executed",
        "entropy": page["entropy_signature"],
        "hash_lock": page["hash_lock"],
        "result": result,
    }