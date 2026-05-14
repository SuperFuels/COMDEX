from fastapi import APIRouter, Query, Request
from typing import List, Optional
from backend.modules.knowledge_graph.replay_renderer import GlyphReplayRenderer

router = APIRouter()


def _apply_permissions(glyphs: List[dict], agent_id: str) -> List[dict]:
    """
    Apply permission tagging and filtering based on requesting agent.
    """
    filtered = []
    for g in glyphs:
        owner = g.get("metadata", {}).get("agent_id", "system")
        private = g.get("metadata", {}).get("private", False)

        # Determine permission state
        if owner == agent_id or agent_id == "system":
            g.setdefault("metadata", {})["permission"] = "editable"
            filtered.append(g)
        elif private:
            # Hidden from non-owners
            g.setdefault("metadata", {})["permission"] = "hidden"
            continue
        else:
            g.setdefault("metadata", {})["permission"] = "read-only"
            filtered.append(g)

    return filtered


@router.get("/api/replay/list")
def get_replay_list(
    request: Request,
    glyph_types: Optional[List[str]] = Query(None),
    include_metadata: bool = True,
    include_trace: bool = True,
    sort_by_time: bool = True,
    limit: Optional[int] = None,
):
    """
    Return a list of glyphs from the current container's replay grid with agent-aware permissions.
    """
    # 🔑 Extract agent identity
    agent_id = request.headers.get("X-Agent-ID", "anonymous")

    renderer = GlyphReplayRenderer()
    glyphs = renderer.render_replay_sequence(
        glyph_types=glyph_types,
        include_metadata=include_metadata,
        include_trace=include_trace,
        sort_by_time=sort_by_time,
        limit=limit,
    )

    # 🔒 Apply permission filtering
    glyphs = _apply_permissions(glyphs, agent_id)

    return {"result": glyphs}


@router.get("/api/replay/trace")
def get_flattened_trace(
    request: Request,
    glyph_type: str = "dream"
):
    """
    Return a flattened replay trace of the given glyph type with agent-aware permissions.
    """
    agent_id = request.headers.get("X-Agent-ID", "anonymous")
    renderer = GlyphReplayRenderer()
    trace_glyphs = renderer.get_replay_as_trace(glyph_type=glyph_type)

    filtered = _apply_permissions(trace_glyphs, agent_id)
    return {"trace": filtered}


@router.get("/api/replay/stats")
def get_replay_stats():
    """
    Return glyph type counts from the current container.
    """
    renderer = GlyphReplayRenderer()
    return {"stats": renderer.get_replay_stats()}