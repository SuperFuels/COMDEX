from typing import Dict, List, Tuple
from datetime import datetime

class GHXPacketValidator:
    REQUIRED_FIELDS = ["ghx_id", "glyphs", "meta"]
    REQUIRED_META = ["created_by", "entropy_score", "hologram_ready"]

    def __init__(self, ghx_packet: Dict):
        self.packet = ghx_packet
        self.errors = []
        self.warnings = []

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        self._check_required_fields()
        self._validate_glyphs()
        self._validate_meta()
        self._check_entanglement()
        self._check_entropy_score()
        return (len(self.errors) == 0, self.errors, self.warnings)

    def _check_required_fields(self):
        for field in self.REQUIRED_FIELDS:
            if field not in self.packet:
                self.errors.append(f"Missing required field: {field}")

    def _validate_glyphs(self):
        glyphs = self.packet.get("glyphs", [])
        if not glyphs:
            self.errors.append("GHX packet contains no glyphs.")
        seen_ids = set()
        for g in glyphs:
            if "id" not in g or "glyph" not in g:
                self.errors.append(f"Glyph missing id or glyph symbol: {g}")
            if g.get("id") in seen_ids:
                self.errors.append(f"Duplicate glyph ID: {g.get('id')}")
            seen_ids.add(g.get("id"))

    def _validate_meta(self):
        meta = self.packet.get("meta", {})
        for field in self.REQUIRED_META:
            if field not in meta:
                self.errors.append(f"Missing meta field: {field}")
        if not meta.get("created_by"):
            self.errors.append("GHX meta must include 'created_by'.")
        if not meta.get("hologram_ready", False):
            self.warnings.append("GHX packet is not marked hologram_ready.")

    def _check_entanglement(self):
        glyphs = self.packet.get("glyphs", [])
        entangled_ids = set()
        for g in glyphs:
            for e in g.get("entangled", []):
                entangled_ids.add(e)
        missing = [eid for eid in entangled_ids if not any(g["id"] == eid for g in glyphs)]
        if missing:
            self.warnings.append(f"Entangled glyphs missing from packet: {missing}")

    def _check_entropy_score(self):
        score = self.packet.get("meta", {}).get("entropy_score", 0)
        if score < 0.5:
            self.warnings.append("Entropy score low — may not compress optimally.")

    def export_validation_log(self) -> Dict:
        return {
            "validated_at": datetime.utcnow().isoformat(),
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }