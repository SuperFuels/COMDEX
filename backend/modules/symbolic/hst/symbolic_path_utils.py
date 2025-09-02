from typing import List, Dict, Optional


def build_symbolic_path_chain(container: dict, trace_key: str = "logic_trace") -> List[dict]:
    """
    Traverse a trace structure (like logic_trace) in the container and reconstruct
    the ordered symbolic mutation/reasoning path from root to most recent.

    Each trace should include a unique 'trace_id' and optional 'parent_id'.
    """
    trace_entries = container.get(trace_key, [])
    if not trace_entries or not isinstance(trace_entries, list):
        return []

    # Index by trace_id for fast lookup
    trace_by_id = {entry.get("trace_id"): entry for entry in trace_entries if "trace_id" in entry}

    # Find the most recent trace (leaf with no children)
    children = {entry.get("parent_id") for entry in trace_entries if entry.get("parent_id")}
    leaves = [e for e in trace_entries if e.get("trace_id") not in children]

    if not leaves:
        return []

    # For now just take the latest leaf (could be expanded for branching later)
    current = leaves[-1]
    chain = [current]

    # Walk backward via parent_id
    while current.get("parent_id"):
        parent_id = current["parent_id"]
        parent = trace_by_id.get(parent_id)
        if not parent:
            break
        chain.append(parent)
        current = parent

    # Return in chronological order (root → latest)
    return list(reversed(chain))


def get_latest_trace(container: dict, trace_key: str = "logic_trace") -> Optional[dict]:
    """
    Get the most recent logic trace (without children).
    """
    trace_entries = container.get(trace_key, [])
    if not trace_entries or not isinstance(trace_entries, list):
        return None

    children = {entry.get("parent_id") for entry in trace_entries if entry.get("parent_id")}
    leaves = [e for e in trace_entries if e.get("trace_id") not in children]

    return leaves[-1] if leaves else None