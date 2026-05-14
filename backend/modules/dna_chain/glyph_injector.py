# backend/modules/dna_chain/glyph_injector.py

import datetime
from typing import Optional, Dict, Any
from backend.modules.state_manager import get_active_universal_container_system
from backend.modules.utils.id_utils import generate_uuid
from backend.modules.utils.time_utils import get_current_timestamp
from backend.modules.dna_chain.container_index_writer import add_to_index

class KnowledgeGraphWriter:
    def __init__(self):
        self.container = get_active_container()

    def inject_glyph(
        self,
        content: str,
        glyph_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        spatial_location: Optional[str] = None,
        prediction: Optional[str] = None,
    ):
        """
        Inject a glyph into the active container's knowledge grid.
        Args:
            content: Core glyph content (symbolic string or logic)
            glyph_type: Type of glyph (e.g., dream, failure, emotion, dna)
            metadata: Optional dictionary with additional context (e.g. cause, intensity)
            spatial_location: Optional 4D symbolic label (e.g. "zone.alpha.4")
            prediction: If present, indicates this is a predictive glyph
        """
        glyph_id = generate_uuid()
        timestamp = get_current_timestamp()
        entry = {
            "id": glyph_id,
            "type": glyph_type,
            "content": content,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }

        if spatial_location:
            entry["spatial"] = spatial_location

        if prediction:
            entry["prediction"] = prediction

        # Inject into active container
        self._write_to_container(entry)

        # Add to master knowledge index
        add_to_index("knowledge_index.glyph", entry)

        return glyph_id

    def _write_to_container(self, entry: Dict[str, Any]):
        if "glyph_grid" not in self.container:
            self.container["glyph_grid"] = []

        self.container["glyph_grid"].append(entry)

        # Optional: mark container as updated or dirty
        self.container["last_updated"] = datetime.datetime.utcnow().isoformat()

    def inject_self_reflection(self, message: str, trigger: str):
        """
        Write a self-reflective glyph into the knowledge graph.
        """
        return self.inject_glyph(
            content=f"Reflection: {message}",
            glyph_type="self_reflection",
            metadata={"trigger": trigger}
        )

    def inject_prediction(self, hypothesis: str, based_on: str):
        """
        Add a predictive glyph suggesting a future path or hypothesis.
        """
        return self.inject_glyph(
            content=hypothesis,
            glyph_type="predictive",
            metadata={"based_on": based_on},
            prediction="future"
        )