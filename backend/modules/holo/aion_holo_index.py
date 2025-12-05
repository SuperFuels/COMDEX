# backend/modules/holo/aion_holo_index.py
# ================================================================
# 📚 Aion Holo Index - list/search AION memory .holo snapshots
# ================================================================
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


HOLO_ROOT = Path("data/holo")
AION_CONTAINER_ID = "aion_memory::core"


def _safe_load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception:
        return None


def list_aion_holos(
    tag: Optional[str] = None,
    seed_id_contains: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Scan data/holo/aion_memory::core/*.holo.json and return a small index.

    Each entry is a summary:
      - holo_id, tick, revision, created_at
      - memory_seed_count, rulebook_seed_count
      - path (for debugging)
      - tags: union of seed tags (for simple filtering)
    """
    container_dir = HOLO_ROOT / AION_CONTAINER_ID
    if not container_dir.exists():
        return []

    # newest first by mtime
    holo_paths = sorted(
        container_dir.glob("*.holo.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    results: List[Dict[str, Any]] = []

    for path in holo_paths:
        data = _safe_load_json(path)
        if not data:
            continue

        meta_container = (
            data.get("metadata", {})
            .get("container", {})
        )

        memory_seeds = meta_container.get("memory_seeds", []) or []
        rulebook_seeds = meta_container.get("rulebook_seeds", []) or []

        # Collect tags from all seeds for simple search
        all_tags: List[str] = []
        for seed in memory_seeds:
            all_tags.extend(seed.get("tags", []) or [])
        for seed in rulebook_seeds:
            all_tags.extend(seed.get("tags", []) or [])
        # de-dupe while preserving order
        seen = set()
        tags_unique: List[str] = []
        for t in all_tags:
            if t not in seen:
                seen.add(t)
                tags_unique.append(t)

        # Simple filters
        if tag:
            if tag not in tags_unique:
                # also allow "keyword:foo" loose match on seed keywords
                if not any(
                    tag in (seed.get("label", "") or "")
                    or tag in " ".join(
                        (seed.get("payload", {}) or {}).get("keywords", []) or []
                    )
                    for seed in memory_seeds
                ):
                    continue

        if seed_id_contains:
            # require at least one seed whose id/label contains this
            match_found = False
            for seed in memory_seeds + rulebook_seeds:
                sid = seed.get("seed_id", "") or ""
                label = seed.get("label", "") or ""
                if (
                    seed_id_contains in sid
                    or seed_id_contains in label
                ):
                    match_found = True
                    break
            if not match_found:
                continue

        item = {
            "holo_id": data.get("holo_id"),
            "container_id": data.get("container_id"),
            "tick": data.get("tick", 0),
            "revision": data.get("revision", 0),
            "created_at": data.get("created_at"),
            "memory_seed_count": len(memory_seeds),
            "rulebook_seed_count": len(rulebook_seeds),
            "path": str(path),
            "tags": tags_unique,
        }

        results.append(item)
        if len(results) >= limit:
            break

    return results