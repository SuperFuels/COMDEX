# backend/modules/lean/lean_ghx.py
import os, json, hashlib, time
from typing import Any, Dict, List

# Prefer your real encoder if available; fall back to simple bundle
try:
    from backend.modules.holograms.ghx_encoder import encode_packet  # type: ignore
    _HAS_ENCODER = True
except Exception:
    _HAS_ENCODER = False
    def encode_packet(payload: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {"type": "GHX_PACKET", "payload": payload}

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def theorem_to_packet(entry: Dict[str, Any], *, container_id: str | None, source_path: str | None) -> Dict[str, Any]:
    base = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "lean.theorem",
        "container_id": container_id,
        "source_path": source_path,
        "name": entry.get("name"),
        "symbol": entry.get("symbol"),
        "logic_raw": entry.get("logic_raw") or entry.get("logic"),
        "logic_norm": (entry.get("codexlang") or {}).get("normalized") or entry.get("logic"),
        "depends_on": entry.get("depends_on", []),
        "body": entry.get("body", ""),
    }
    base["id"] = f"ghx:{_sha(json.dumps(base, ensure_ascii=False))}"
    return encode_packet(base) if _HAS_ENCODER else base

def dump_packets(entries: List[Dict[str, Any]], out_dir: str, *, container_id: str | None, source_path: str | None) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []
    for e in entries:
        pkt = theorem_to_packet(e, container_id=container_id, source_path=source_path)
        name = e.get("name") or "theorem"
        p = os.path.join(out_dir, f"{name}.ghx.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(pkt, f, indent=2, ensure_ascii=False)
        paths.append(p)
    return paths

def bundle_packets(entries: List[Dict[str, Any]], out_file: str, *, container_id: str | None, source_path: str | None) -> str:
    os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)
    bundle = [theorem_to_packet(e, container_id=container_id, source_path=source_path) for e in entries]
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "GHX_BUNDLE", "items": bundle}, f, indent=2, ensure_ascii=False)
    return out_file