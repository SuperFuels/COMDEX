from fastapi import APIRouter, Query
from typing import List, Optional
from backend.modules.knowledge_graph.replay_renderer import GlyphReplayRenderer

router = APIRouter()


@router.get("/api/replay/list")
def get_replay_list(
    glyph_types: Optional[List[str]] = Query(None),
    include_metadata: bool = True,
    include_trace: bool = True,
    sort_by_time: bool = True,
    limit: Optional[int] = None,
):
    """
    Return a list of glyphs from the current container's replay grid.

    Query Parameters:
    - glyph_types: Filter list (e.g., ?glyph_types=dream&glyph_types=emotion)
    - include_metadata: Whether to include metadata fields
    - include_trace: Whether to include trace_ref if present
    - sort_by_time: Sort by timestamp
    - limit: Limit number of results
    """
    renderer = GlyphReplayRenderer()
    return {
        "result": renderer.render_replay_sequence(
            glyph_types=glyph_types,
            include_metadata=include_metadata,
            include_trace=include_trace,
            sort_by_time=sort_by_time,
            limit=limit,
        )
    }


@router.get("/api/replay/trace")
def get_flattened_trace(
    glyph_type: str = "dream"
):
    """
    Return a flattened replay trace of the given glyph type.
    """
    renderer = GlyphReplayRenderer()
    return {
        "trace": renderer.get_replay_as_trace(glyph_type=glyph_type)
    }


@router.get("/api/replay/stats")
def get_replay_stats():
    """
    Return glyph type counts from the current container.
    """
    renderer = GlyphReplayRenderer()
    return {
        "stats": renderer.get_replay_stats()
    }