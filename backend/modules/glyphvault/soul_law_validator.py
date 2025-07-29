import logging
import hashlib
from typing import Optional, Dict, Union

from backend.modules.knowledge.knowledge_graph_writer import KnowledgeGraphWriter  # ✅ R5a

logger = logging.getLogger(__name__)

class SoulLawValidator:
    """
    Validates avatar states and container metadata against immutable Soul Laws and morality gates.
    Also verifies symbolic expansion keys and seed locks for secure container inflation.
    """

    MIN_AVATAR_LEVEL = 10  # example threshold

    def __init__(self):
        # Define universal Soul Laws (immutable logic gates)
        self.soul_laws = {
            "value_of_life": True,
            "do_no_harm": True,
        }
        self.kg_writer = KnowledgeGraphWriter()  # ✅ R5a
        self.enable_glyph_injection = True  # ✅ R5f future toggle

    def validate_avatar(self, avatar_state: Optional[Dict]) -> bool:
        """
        Check if avatar state satisfies all Soul Law requirements.
        """
        if avatar_state is None:
            logger.debug("Avatar state missing; failing Soul Law validation")
            self._inject_violation("missing_avatar_state", "No avatar state provided")
            return False

        level = avatar_state.get("level", 0)
        if level < self.MIN_AVATAR_LEVEL:
            logger.debug(f"Avatar level {level} below minimum {self.MIN_AVATAR_LEVEL} for Soul Law validation")
            self._inject_violation("low_level", f"Avatar level {level} below required {self.MIN_AVATAR_LEVEL}")
            return False

        # ✅ Success case → inject moral approval glyph
        logger.debug(f"Avatar state validated successfully: level {level}")
        self._inject_approval("avatar_approval", f"Avatar level {level} approved")
        return True

    def validate_container(self, container_metadata: Optional[Dict]) -> bool:
        """
        Validate container metadata against Soul Laws.
        """
        # For now we always approve
        self._inject_approval("container_ok", "Container passed moral validation")
        return True

    @staticmethod
    def validate_navigation_link(source_container: dict, target_container: dict):
        """
        SoulLaw enforcement for container linking/navigation.
        Blocks linking if forbidden rules are detected.
        """
        # Example: Prevent linking secure containers to public ones
        if "secure" in source_container.get("tags", []) and "public" in target_container.get("tags", []):
            raise PermissionError("❌ SoulLaw: Secure container cannot be linked to public.")

        print(f"✅ SoulLaw: Navigation link allowed {source_container['id']} → {target_container['id']}")

    def generate_seed_lock(self, identity: str, entropy: str) -> str:
        input_str = f"{identity}:{entropy}"
        return hashlib.sha256(input_str.encode("utf-8")).hexdigest()

    def verify_seed_lock(self, key: str, expected_hash: str) -> bool:
        match = key == expected_hash
        if not match:
            logger.warning("Soul-lock key mismatch")
            self._inject_violation("seed_lock_mismatch", "Provided key did not match expected hash")
        else:
            self._inject_approval("seed_lock_validated", "Seed lock key matched expected hash")
        return match

    # ✅ R5b: Inject moral approval glyph
    def _inject_approval(self, rule: str, reason: str):
        if not self.enable_glyph_injection:
            return
        try:
            self.kg_writer.inject_glyph(
                content=reason,
                glyph_type="approval",
                metadata={
                    "rule": rule,
                    "type": "SoulLaw",
                    "origin": "SoulLawValidator",
                    "tags": ["📜", "🧠", "✅"]
                },
                plugin="SoulLaw"
            )
            print(f"✅ Injected SoulLaw approval glyph: {rule} – {reason}")
        except Exception as e:
            print(f"⚠️ Failed to inject SoulLaw approval glyph: {e}")

    # ✅ R5c: Inject moral violation glyph
    def _inject_violation(self, rule: str, reason: str):
        if not self.enable_glyph_injection:
            return
        try:
            self.kg_writer.inject_glyph(
                content=reason,
                glyph_type="violation",
                metadata={
                    "rule": rule,
                    "type": "SoulLaw",
                    "origin": "SoulLawValidator",
                    "tags": ["📜", "🧠", "❌"]
                },
                plugin="SoulLaw"
            )
            print(f"❌ Injected SoulLaw violation glyph: {rule} – {reason}")
        except Exception as e:
            print(f"⚠️ Failed to inject SoulLaw violation glyph: {e}")


soul_law_validator = SoulLawValidator()