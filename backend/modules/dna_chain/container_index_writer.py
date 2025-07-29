# File: backend/modules/dna_chain/container_index_writer.py

import datetime
import hashlib
from typing import Dict, Any

from backend.modules.state_manager import get_active_universal_container_system
from backend.modules.utils.time_utils import get_current_timestamp
from backend.modules.utils.id_utils import generate_uuid
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.websocket_manager import WebSocketManager
from backend.modules.soullaw.soul_law_validator import SoulLawValidator

# ✅ WebSocket for live UI updates
ws_manager = WebSocketManager()


def _get_or_create_index(container: Dict[str, Any], index_name: str):
    if "indexes" not in container:
        container["indexes"] = {}
    if index_name not in container["indexes"]:
        container["indexes"][index_name] = []
    return container["indexes"][index_name]


def _create_index_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    glyph_id = entry.get("id", generate_uuid())
    glyph_hash = entry.get("hash", hashlib.sha256(entry["content"].encode()).hexdigest())
    timestamp = entry.get("timestamp", get_current_timestamp())

    return {
        "id": glyph_id,
        "hash": glyph_hash,
        "type": entry.get("type", "unknown"),
        "timestamp": timestamp,
        "tags": entry.get("metadata", {}).get("tags", []),
        "spatial": entry.get("spatial", None),
        "plugin": entry.get("plugin", None),
    }


def add_to_index(index_name: str, entry: Dict[str, Any]):
    """
    Adds a symbolic glyph entry to a container-level index,
    validates Knowledge Graph integrity, syncs UCS state, and emits updates.
    """
    container = get_active_universal_container_system().get("active_container", {})

    # ✅ Create or fetch the target index
    index = _get_or_create_index(container, index_name)
    index_entry = _create_index_entry(entry)
    index.append(index_entry)
    container["last_index_update"] = datetime.datetime.utcnow().isoformat()

    # ✅ Knowledge Graph validation (Rubric check)
    try:
        from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
        kgw = KnowledgeGraphWriter()
        container["rubric_report"] = kgw.validate_knowledge_graph()
    except Exception as e:
        container["rubric_report_error"] = f"Failed to validate rubric: {str(e)}"

    # ✅ SoulLaw enforcement on updated container state
    try:
        SoulLawValidator.validate_container_state(container)
    except Exception as e:
        container["soul_law_error"] = f"SoulLaw validation failed: {str(e)}"

    # ✅ UCS runtime sync (persist updated state)
    try:
        ucs_runtime.save_container(container["id"], container)
        print(f"📥 UCS Sync: Saved updated container state for {container['id']}")
    except Exception as e:
        print(f"⚠️ UCS sync failed: {e}")

    # ✅ GHX visualization log
    try:
        ucs_runtime.visualizer.log_event(container["id"], f"Index updated: {index_name}")
    except Exception as e:
        print(f"⚠️ GHX visualization logging failed: {e}")

    # ✅ WebSocket broadcast for live index updates
    ws_manager.broadcast({
        "type": "index_update",
        "data": {
            "container_id": container.get("id"),
            "index_name": index_name,
            "entry": index_entry,
            "timestamp": get_current_timestamp()
        }
    })

    # ✅ Emit SQI event (index type aware)
    try:
        event_type = f"{index_name}_entry_added"
        from backend.modules.sqi.sqi_event_bus import emit_sqi_event
        emit_sqi_event(event_type, payload={"container_id": container.get("id"), "entry": index_entry})
    except ImportError:
        pass


def add_goal_entry(goal_str: str, source: str = "memory"):
    """
    Adds a symbolic goal entry into the goal index.
    """
    container = get_active_universal_container_system().get("active_container", {})
    goal_id = generate_uuid()

    entry = {
        "id": goal_id,
        "type": "goal",
        "content": goal_str,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "source": source,
            "tags": ["goal"],
        }
    }
    add_to_index("goal_index", entry)
    return goal_id


def add_dream_entry(dream_str: str, category: str = "vision"):
    """
    Adds a dream entry (used in replay/forecast logic).
    """
    container = get_active_universal_container_system().get("active_container", {})
    dream_id = generate_uuid()

    entry = {
        "id": dream_id,
        "type": "dream",
        "content": dream_str,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "category": category,
            "tags": ["dream"],
        }
    }
    add_to_index("dream_index", entry)
    return dream_id


def add_failure_entry(reason: str, caused_by: str = "unknown"):
    """
    Adds a failure entry for error analysis and mutation.
    """
    container = get_active_universal_container_system().get("active_container", {})
    failure_id = generate_uuid()

    entry = {
        "id": failure_id,
        "type": "failure",
        "content": reason,
        "timestamp": get_current_timestamp(),
        "metadata": {
            "cause": caused_by,
            "tags": ["failure"],
        }
    }
    add_to_index("failure_index", entry)
    return failure_id