import json
import uuid
import logging
from typing import Dict, List
from backend.modules.hologram.hologram_engine import generate_holographic_packet

logger = logging.getLogger(__name__)

class GHXSerializer:
    def __init__(self, container_id: str):
        self.container_id = container_id

    def encode_to_ghx(self, glyphs: List[Dict]) -> Dict:
        """
        Converts glyph list into a GHX (Glyph Hologram Exchange) packet.
        """
        if not glyphs:
            logger.warning(f"[GHXSerializer:{self.container_id}] No glyphs provided for encoding.")
            return {}

        ghx_packet = generate_holographic_packet(glyphs)
        logger.info(f"[GHXSerializer:{self.container_id}] Encoded {len(glyphs)} glyphs into GHX packet {ghx_packet.get('ghx_id', 'unknown')}")
        return ghx_packet

    def export_to_dc(self, ghx_packet: Dict, path: str = None) -> str:
        """
        Injects GHX packet into a .dc.json container format.
        """
        if not ghx_packet:
            raise ValueError("Cannot export empty GHX packet")

        dc_data = {
            "container_id": self.container_id,
            "physics": "symbolic-quantum",
            "hologram_packet": ghx_packet,
            "glyphs": ghx_packet.get("glyphs", []),
            "ghx_id": ghx_packet.get("ghx_id"),
            "metadata": {
                "type": "GHX",
                "version": "1.0",
                "exported_at": ghx_packet.get("created_at")
            }
        }

        file_path = path or f"./containers/{self.container_id}.dc.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dc_data, f, indent=2)

        logger.info(f"[GHXSerializer:{self.container_id}] Exported GHX container → {file_path}")
        return file_path

    def import_from_dc(self, file_path: str) -> Dict:
        """
        Loads a GHX packet from an existing .dc.json file.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        packet = data.get("hologram_packet", {})
        logger.info(f"[GHXSerializer:{self.container_id}] Imported GHX packet {packet.get('ghx_id', 'unknown')} from {file_path}")
        return packet

    def validate_ghx(self, ghx_packet: Dict) -> bool:
        """
        Validates the integrity and structure of a GHX packet.
        """
        required_fields = {"ghx_id", "glyphs", "projection_space", "color_logic"}
        valid = required_fields.issubset(set(ghx_packet.keys()))
        logger.info(f"[GHXSerializer:{self.container_id}] Validation {'✅ PASS' if valid else '❌ FAIL'} for GHX {ghx_packet.get('ghx_id', 'unknown')}")
        return valid