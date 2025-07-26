import json
import uuid
from typing import Dict, List
from backend.modules.hologram.hologram_engine import generate_holographic_packet

class GHXSerializer:
    def __init__(self, container_id: str):
        self.container_id = container_id

    def encode_to_ghx(self, glyphs: List[Dict]) -> Dict:
        """
        Converts glyph list into a GHX (Glyph Hologram Exchange) packet.
        """
        ghx_packet = generate_holographic_packet(glyphs)
        return ghx_packet

    def export_to_dc(self, ghx_packet: Dict, path: str = None) -> str:
        """
        Injects GHX packet into a .dc.json container format.
        """
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
        return file_path

    def import_from_dc(self, file_path: str) -> Dict:
        """
        Loads a GHX packet from an existing .dc.json file.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("hologram_packet", {})

    def validate_ghx(self, ghx_packet: Dict) -> bool:
        """
        Validates the integrity and structure of a GHX packet.
        """
        required_fields = {"ghx_id", "glyphs", "projection_space", "color_logic"}
        return required_fields.issubset(set(ghx_packet.keys()))