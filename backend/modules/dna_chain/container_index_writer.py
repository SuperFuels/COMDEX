# File: backend/modules/dna_chain/container_index_writer.py

import datetime
from typing import Dict, Any
from backend.modules.state_manager import get_active_container
from backend.modules.utils.time_utils import get_current_timestamp
from backend.modules.utils.id_utils import generate_uuid
import hashlib


def _get_or_create_index(container: Dict[str, Any], index_name: str):
    if "indexes" not in container:
        container["indexes"] = {}
    if index_name not in container["indexes"]:
        container["indexes"][index_name] = []
    return container["indexes"][index_name]

def add_to_index(index_name: str, entry: Dict[str, Any]):
    """
    Adds a symbolic glyph entry to a container-level index.
    """
    container = get_active_container()
    index = _get_or_create_index(container, index_name)
    index_entry = _create_index_entry(entry)
    index.append(index_entry)
    container["last_index_update"] = datetime.datetime.utcnow().isoformat()

    # ⬇️ NEW: Inject rubric report
    try:
        from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
        kgw = KnowledgeGraphWriter()
        container["rubric_report"] = kgw.validate_knowledge_graph()
    except Exception as e:
        container["rubric_report_error"] = f"Failed to validate rubric: {str(e)}"

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
    Adds a symbolic glyph entry to a container-level index.
    """
    container = get_active_container()
    index = _get_or_create_index(container, index_name)
    index_entry = _create_index_entry(entry)
    index.append(index_entry)
    container["last_index_update"] = datetime.datetime.utcnow().isoformat()


def add_goal_entry(goal_str: str, source: str = "memory"):
    """
    Adds a symbolic goal entry into the goal index.
    """
    container = get_active_container()
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
    container = get_active_container()
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
    container = get_active_container()
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