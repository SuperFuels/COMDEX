# File: backend/modules/sci/container_workspace_loader.py

import json
import logging
from typing import Optional, Dict, Any

from backend.modules.container.container_runtime import activate_container
from backend.modules.codex.codex_executor import execute_codex_scroll
from backend.modules.hologram.ghx_replay_broadcast import broadcast_ghx_container_load
from backend.modules.qfc.qfc_overlay_engine import inject_qfc_overlay
from backend.modules.sqi.sqi_scorer import inject_sqi_scores_into_container
from backend.modules.patterns.pattern_registry import detect_and_register_patterns
from backend.modules.kg.kg_writer_singleton import get_kg_writer
from backend.modules.websocket.websocket_broadcast import send_codex_ws_event

logger = logging.getLogger(__name__)

class ContainerWorkspaceLoader:
    def __init__(self):
        self.active_container: Optional[Dict[str, Any]] = None
        self.active_container_id: Optional[str] = None

    def load_container_from_file(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                container = json.load(f)
            logger.info(f"[ContainerLoader] Loaded container from: {path}")
            return container
        except Exception as e:
            logger.error(f"[ContainerLoader] Failed to load container: {e}")
            raise

    def activate_workspace(self, container: Dict[str, Any], container_id: Optional[str] = None):
        """
        Main entry point to load a .dc.json container into the SCI field runtime.
        Injects into QFC, triggers GHX replay, activates glyph field.
        """
        try:
            self.active_container = container
            self.active_container_id = container_id or container.get("id", "unknown")

            # 🔹 Inject SQI scores into symbolic elements
            inject_sqi_scores_into_container(container)

            # 🔹 Detect patterns, register into pattern registry
            detect_and_register_patterns(container)

            # 🔹 Inject QFC overlays
            inject_qfc_overlay(container)

            # 🔹 Broadcast GHX projection (for HUD replay)
            broadcast_ghx_container_load(container)

            # 🔹 Activate symbolic runtime
            activate_container(container)

            # 🔹 Optionally fire boot scroll
            boot_scroll = container.get("boot_scroll")
            if boot_scroll:
                execute_codex_scroll(boot_scroll)

            # 🔹 Inject into KG
            get_kg_writer().inject_container(container)

            # 🔹 WebSocket HUD
            send_codex_ws_event("container_loaded", {
                "container_id": self.active_container_id,
                "glyph_count": len(container.get("glyphs", [])),
                "status": "active"
            })

            logger.info(f"[ContainerLoader] Activated workspace: {self.active_container_id}")

        except Exception as e:
            logger.exception(f"[ContainerLoader] Workspace activation failed: {e}")
            raise

    def get_active_container(self) -> Optional[Dict[str, Any]]:
        return self.active_container

    def clear(self):
        logger.info("[ContainerLoader] Clearing active workspace.")
        self.active_container = None
        self.active_container_id = None


# 🔁 Singleton for SCI usage
container_workspace_loader = ContainerWorkspaceLoader()