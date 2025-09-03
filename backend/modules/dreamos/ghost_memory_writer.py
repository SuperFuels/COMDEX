import json
import os
from datetime import datetime
from backend.modules.utils.container_io import load_container, save_container

def inject_ghost_memory(container_id: str, ghost_trace: str) -> str:
    """
    Inject ghost trace as a memory scroll into the container's memory section.
    """
    container = load_container(container_id)
    memory = container.setdefault("memory", {})
    scrolls = memory.setdefault("scrolls", [])

    scroll_entry = {
        "type": "ghost_replay",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "content": json.loads(ghost_trace),
    }

    scrolls.append(scroll_entry)
    save_container(container_id, container)

    return f"ghost-scroll-{len(scrolls)}"