# backend/modules/glyphvault/soul_law_validator.py

import os
import logging
import hashlib
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 🌐 Check if running in test mode
SOUL_LAW_MODE = os.getenv("SOUL_LAW_MODE", "full").lower()

if SOUL_LAW_MODE == "full":
    from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter  # ✅ Original import
else:
    # ✅ Test mode stub: Prints glyph events instead of injecting into IGI
    class KnowledgeGraphWriter:
        def inject_glyph(self, *args, **kwargs):
            print(f"[SIM] SoulLaw glyph (test mode): {kwargs.get('metadata', {}).get('rule', 'unknown')}")

    print("⚠️ SoulLaw running in TEST MODE: Using stubbed KnowledgeGraphWriter")


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
        self.kg_writer = KnowledgeGraphWriter()  # ✅ Knowledge Graph integration (stub if test mode)
        self.enable_glyph_injection = True  # ✅ Toggle for injecting glyph logs

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
        # For now always approve, with glyph logging
        self._inject_approval("container_ok", "Container passed moral validation")
        return True

    @staticmethod
    def validate_navigation_link(source_container: dict, target_container: dict):
        """
        SoulLaw enforcement for container linking/navigation.
        Blocks linking if forbidden rules are detected.
        """
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

    # ✅ Inject moral approval glyph into Knowledge Graph or test stub
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

    # ✅ Inject moral violation glyph into Knowledge Graph or test stub
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


# ✅ Exported singleton instance
soul_law_validator = SoulLawValidator()

# 🔒 Warn if running test mode in production accidentally
if SOUL_LAW_MODE == "test":
    print("⚠️ WARNING: SoulLawValidator is running in TEST MODE. Switch to full mode for production (SOUL_LAW_MODE=full).")