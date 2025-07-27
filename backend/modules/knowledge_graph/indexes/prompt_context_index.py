"""
📄 prompt_context_index.py

Design Rubric:
- ✅ Self-contained module for managing AION prompt context trace
- ✅ Injects symbolic reasoning inputs into `.dc` containers
- ✅ Used by: aion_prompt_engine.py
"""

from typing import List, Dict
from backend.modules.dna_chain.container_index_writer import add_to_index
from datetime import datetime

PLUGIN_ID = "aion_prompt_engine"

def add_prompt_context_entry(context_blocks: List[Dict[str, str]], source: str = "aion_prompt_engine"):
    """
    Adds a prompt context entry from a list of GPT-style message blocks.
    Typically includes system + user + skills injection.

    Args:
        context_blocks: List of message dicts (role/content pairs).
        source: Source identifier (default = "aion_prompt_engine").
    """
    context_str = "\n\n".join(
        [f"[{block['role']}]: {block['content']}" for block in context_blocks]
    )

    entry = {
        "id": f"prompt-{datetime.utcnow().isoformat()}",
        "type": "prompt_context",
        "content": context_str,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "source": source,
            "plugin": PLUGIN_ID,
            "tags": ["prompt", "context", "identity", "skill"]
        }
    }
    add_to_index("prompt_context_index", entry)