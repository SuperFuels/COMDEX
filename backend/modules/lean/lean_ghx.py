# backend/modules/lean/lean_ghx.py

import os
import json
import hashlib
import time
from typing import Any, Dict, List, Optional

# Prefer your real encoder if available; fall back to simple bundle
try:
    from backend.modules.holograms.ghx_encoder import encode_packet  # type: ignore
    _HAS_ENCODER = True
except Exception:
    _HAS_ENCODER = False

    def encode_packet(payload: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {"type": "GHX_PACKET", "payload": payload}


def _sha(s: str) -> str:
    """Short SHA256 for deterministic IDs."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def _safe_name(s: str) -> str:
    s = (s or "").strip() or "theorem"
    # allow alnum, _, -, .
    s = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in s)
    return s[:120]  # keep filenames sane


def theorem_to_packet(
    entry: Dict[str, Any],
    *,
    container_id: Optional[str],
    source_path: Optional[str],
    extra_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert a Lean theorem entry -> GHX packet."""
    logic_raw = entry.get("logic_raw") or entry.get("logic") or ""
    codexlang = entry.get("codexlang") or {}

    # Prefer the same normalized string you write into containers/ledger
    logic_norm = (
        codexlang.get("normalized")
        or entry.get("codexlang_string")
        or entry.get("logic")
        or logic_raw
    )

    base: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "lean.theorem",
        "container_id": container_id,
        "source_path": source_path,
        "name": entry.get("name"),
        # lean_to_glyph emits glyph_symbol ("⟦ Theorem ⟧" / "⟦ Axiom ⟧") not always "symbol"
        "symbol": entry.get("glyph_symbol") or entry.get("symbol") or "⟦ Theorem ⟧",
        "logic_raw": logic_raw,
        "logic_norm": logic_norm,
        "depends_on": entry.get("depends_on", []),
        "body": entry.get("body", ""),
        "meta": {
            "leanProof": True,  # UI badge / symbolic detector flag
            "source": "lean_proof_embed",
            # Prefer upstream semantic hash if present, else derive one
            "sha": entry.get("hash") or _sha(logic_norm + (entry.get("body") or "")),
            "encoded": _HAS_ENCODER,
        },
    }

    if extra_meta:
        base["meta"].update(extra_meta)

    # Stable ID using canonical JSON
    base["id"] = f"ghx:{_sha(json.dumps(base, sort_keys=True, ensure_ascii=False))}"

    return encode_packet(base) if _HAS_ENCODER else base


def dump_packets(
    entries: List[Dict[str, Any]],
    out_dir: str,
    *,
    container_id: Optional[str],
    source_path: Optional[str],
) -> List[str]:
    """Dump each theorem entry as an individual .ghx.json packet."""
    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []

    for e in entries:
        pkt = theorem_to_packet(e, container_id=container_id, source_path=source_path)

        name = _safe_name(e.get("name") or "theorem")
        suffix = (
            (e.get("hash") or _sha((e.get("logic_raw") or e.get("logic") or "") + (e.get("body") or "")))
        )[:8]
        p = os.path.join(out_dir, f"{name}.{suffix}.ghx.json")

        with open(p, "w", encoding="utf-8") as f:
            json.dump(pkt, f, indent=2, ensure_ascii=False)

        paths.append(p)

    return paths


def bundle_packets(
    entries: List[Dict[str, Any]],
    out_file: str,
    *,
    container_id: Optional[str],
    source_path: Optional[str],
) -> str:
    """Bundle all theorem entries into a single GHX_BUNDLE file."""
    os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)

    bundle = [
        theorem_to_packet(e, container_id=container_id, source_path=source_path)
        for e in entries
    ]

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"type": "GHX_BUNDLE", "items": bundle}, f, indent=2, ensure_ascii=False)

    return out_file