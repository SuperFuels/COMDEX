from fastapi import APIRouter, Query
from typing import Any
from backend.modules.collapse.collapse_trace_exporter import get_recent_collapse_traces

router = APIRouter()

@router.get("/api/collapse_traces/recent")
def fetch_collapse_traces(show_collapsed: bool = Query(True)) -> Any:
    """
    Fetch collapse traces, optionally filtering collapsed beams.
    Returns grouped/tick-ordered replay-ready format.
    """
    return get_recent_collapse_traces(show_collapsed=show_collapsed)