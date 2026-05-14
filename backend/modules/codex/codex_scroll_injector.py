# File: backend/modules/codex/codex_scroll_injector.py

from typing import Dict, Any, Optional
from backend.modules.codex.codex_scroll_library import save_named_scroll
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

def inject_scroll(scroll: Dict[str, Any], name: Optional[str] = None, container_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Inject a scroll into Codex persistence + Knowledge Graph.
    - Saves to codex_scroll_library
    - Writes to KG for semantic traceability
    """
    try:
        if name:
            save_named_scroll(name, scroll)

        kg_writer = get_kg_writer()
        kg_writer.write_scroll(scroll, container_id=container_id)

        return {"status": "success", "detail": f"Scroll injected {name or '[anonymous]'}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}