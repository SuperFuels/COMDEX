"""
📄 tag_index.py

🔖 Knowledge Graph Tag Index
Indexes glyphs by tags for fast lookup and semantic filtering.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Tag-to-Glyph Mapping
✅ Multi-Tag Intersection & Union Queries
✅ Rebuild from Container Glyph Grids
✅ Auto-Sync with Knowledge Index
✅ Ready for Cross-Container Tag Queries
"""

from typing import Dict, List, Set, Any
import logging
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter  # ✅ Added for direct glyph retrieval

logger = logging.getLogger(__name__)

# 🔖 In-memory tag index: { tag -> set(glyph_ids) }
TAG_INDEX: Dict[str, Set[str]] = {}

# 🔖 Glyph metadata store: { glyph_id -> glyph_entry }
GLYPH_META: Dict[str, Dict[str, Any]] = {}


def add_tag_entry(glyph_id: str, tags: List[str], glyph_entry: Dict[str, Any]):
    """
    Add a glyph and its tags to the tag index.
    """
    GLYPH_META[glyph_id] = glyph_entry
    for tag in tags:
        TAG_INDEX.setdefault(tag, set()).add(glyph_id)
    logger.debug(f"[TagIndex] Added glyph {glyph_id} with tags: {tags}")


def remove_tag_entry(glyph_id: str):
    """
    Remove a glyph from the tag index.
    """
    if glyph_id in GLYPH_META:
        glyph_entry = GLYPH_META.pop(glyph_id)
        tags = glyph_entry.get("tags", [])
        for tag in tags:
            if tag in TAG_INDEX and glyph_id in TAG_INDEX[tag]:
                TAG_INDEX[tag].remove(glyph_id)
                if not TAG_INDEX[tag]:  # prune empty tags
                    del TAG_INDEX[tag]
        logger.debug(f"[TagIndex] Removed glyph {glyph_id}")


def query_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    Return all glyphs associated with a single tag.
    """
    glyph_ids = TAG_INDEX.get(tag, set())
    return [GLYPH_META[g] for g in glyph_ids]


def query_multi_tags(tags: List[str], mode: str = "and") -> List[Dict[str, Any]]:
    """
    Search for glyphs matching multiple tags.
    mode = "and" -> intersection
    mode = "or"  -> union
    """
    if not tags:
        return []

    if mode == "and":
        sets = [TAG_INDEX.get(tag, set()) for tag in tags]
        common = set.intersection(*sets) if sets else set()
        return [GLYPH_META[g] for g in common]

    elif mode == "or":
        combined = set()
        for tag in tags:
            combined |= TAG_INDEX.get(tag, set())
        return [GLYPH_META[g] for g in combined]

    else:
        raise ValueError("Invalid mode: choose 'and' or 'or'")


def rebuild_from_glyphs(glyph_grid: List[Dict[str, Any]]):
    """
    Rebuild the tag index from a glyph grid (e.g. during container load).
    """
    TAG_INDEX.clear()
    GLYPH_META.clear()

    for glyph in glyph_grid:
        glyph_id = glyph.get("id") or glyph.get("glyph")
        tags = glyph.get("tags", [])
        if glyph_id:
            add_tag_entry(glyph_id, tags, glyph)

    logger.info(f"[TagIndex] Rebuilt from {len(glyph_grid)} glyphs. Tags: {list(TAG_INDEX.keys())}")


def list_tags() -> List[str]:
    """
    Return all available tags.
    """
    return sorted(TAG_INDEX.keys())


def glyphs_for_tag(tag: str) -> List[str]:
    """
    Return just glyph IDs for a given tag.
    """
    return sorted(list(TAG_INDEX.get(tag, set())))


def get_glyphs_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    🔍 Direct fetch: Retrieve glyphs from the active KnowledgeGraphWriter container by tag.
    Useful for modules needing live container glyph queries outside prebuilt index.
    """
    kg = KnowledgeGraphWriter()
    glyphs = kg.container.get("glyph_grid", [])
    return [g for g in glyphs if tag in g.get("tags", [])]