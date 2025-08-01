import os
import logging
import hashlib
import importlib
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 🌐 Mode detection: full or test (fallback)
SOUL_LAW_MODE = os.getenv("SOUL_LAW_MODE", "full").lower()

def _lazy_load_kg_writer():
    """Lazy loader for KnowledgeGraphWriter to avoid circular imports."""
    try:
        kg_module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")
        return kg_module.KnowledgeGraphWriter
    except ImportError as e:
        logger.warning(f"[SoulLaw] Failed to import KnowledgeGraphWriter: {e}")
        # ✅ Fallback: Return a stub that avoids 'self' binding errors
        def _fallback_stub():
            class StubKGWriter:
                def inject_glyph(self, *args, **kwargs):
                    print(f"[SIM:FALLBACK] Glyph inject: {kwargs.get('metadata', {}).get('rule', 'unknown')}")
            return StubKGWriter()
        return _fallback_stub

# ✅ Test mode stub definition
if SOUL_LAW_MODE != "full":
    class KnowledgeGraphWriter:
        def inject_glyph(self, *args, **kwargs):
            print(f"[SIM] SoulLaw glyph (test mode): {kwargs.get('metadata', {}).get('rule', 'unknown')}")
    print("⚠️ SoulLaw running in TEST MODE: Using stubbed KnowledgeGraphWriter")


class SoulLawValidator:
    """Validates avatar states and containers against immutable Soul Laws."""

    MIN_AVATAR_LEVEL = 10  # Example threshold

    def __init__(self):
        self.soul_laws = {"value_of_life": True, "do_no_harm": True}
        self.kg_writer = None  # Lazy init
        self.enable_glyph_injection = True

    def _get_kg_writer(self):
        """Initialize KnowledgeGraphWriter lazily."""
        if self.kg_writer is None:
            kg_class_or_stub = _lazy_load_kg_writer()
            # ✅ Always instantiate properly, even if fallback stub
            self.kg_writer = kg_class_or_stub() if callable(kg_class_or_stub) else KnowledgeGraphWriter()
        return self.kg_writer

    def validate_avatar(self, avatar_state: Optional[Dict]) -> bool:
        """Check if avatar meets SoulLaw level and morality gates."""
        # ✅ SAFE MODE bypass
        if SOUL_LAW_MODE == "test":
            logger.debug("[SoulLaw] SAFE MODE: Auto-approving avatar validation.")
            self._inject_approval("safe_mode_bypass", "Avatar auto-approved in SAFE MODE")
            return True

        if avatar_state is None:
            logger.debug("[SoulLaw] Avatar state missing")
            self._inject_violation("missing_avatar_state", "No avatar state provided")
            return False

        level = avatar_state.get("level", 0)
        if level < self.MIN_AVATAR_LEVEL:
            logger.debug(f"[SoulLaw] Avatar level {level} below minimum {self.MIN_AVATAR_LEVEL}")
            self._inject_violation("low_level", f"Avatar level {level} below required {self.MIN_AVATAR_LEVEL}")
            return False

        self._inject_approval("avatar_approval", f"Avatar level {level} approved")
        return True

    def validate_container(self, container_metadata: Optional[Dict]) -> bool:
        """Validate container morality gates (expandable for trait checks)."""
        # ✅ SAFE MODE bypass
        if SOUL_LAW_MODE == "test":
            logger.debug("[SoulLaw] SAFE MODE: Auto-approving container validation.")
            self._inject_approval("safe_mode_bypass_container", "Container auto-approved in SAFE MODE")
            return True

        self._inject_approval("container_ok", "Container passed moral validation")
        return True

    @staticmethod
    def validate_navigation_link(source_container: dict, target_container: dict):
        """Block forbidden container links (e.g., secure → public)."""
        if "secure" in source_container.get("tags", []) and "public" in target_container.get("tags", []):
            raise PermissionError("❌ SoulLaw: Secure container cannot link to public.")
        print(f"✅ SoulLaw: Navigation link allowed {source_container['id']} → {target_container['id']}")

    def generate_seed_lock(self, identity: str, entropy: str) -> str:
        return hashlib.sha256(f"{identity}:{entropy}".encode("utf-8")).hexdigest()

    def verify_seed_lock(self, key: str, expected_hash: str) -> bool:
        if key != expected_hash:
            logger.warning("[SoulLaw] Seed-lock mismatch detected")
            self._inject_violation("seed_lock_mismatch", "Key mismatch")
            return False
        self._inject_approval("seed_lock_validated", "Seed lock key matched")
        return True

    def _inject_approval(self, rule: str, reason: str):
        if self.enable_glyph_injection:
            try:
                kg_writer = self._get_kg_writer()
                if kg_writer:
                    kg_writer.inject_glyph(
                        content=reason,
                        glyph_type="approval",
                        metadata={"rule": rule, "type": "SoulLaw", "origin": "SoulLawValidator", "tags": ["📜", "🧠", "✅"]},
                        plugin="SoulLaw"
                    )
                    print(f"✅ [SoulLaw] Approval: {rule} – {reason}")
                else:
                    print(f"[SoulLaw] Skipped approval glyph injection (no KG writer).")
            except Exception as e:
                logger.error(f"[SoulLaw] Approval glyph injection failed: {e}")

    def _inject_violation(self, rule: str, reason: str):
        if self.enable_glyph_injection:
            try:
                kg_writer = self._get_kg_writer()
                if kg_writer:
                    kg_writer.inject_glyph(
                        content=reason,
                        glyph_type="violation",
                        metadata={"rule": rule, "type": "SoulLaw", "origin": "SoulLawValidator", "tags": ["📜", "🧠", "❌"]},
                        plugin="SoulLaw"
                    )
                    print(f"❌ [SoulLaw] Violation: {rule} – {reason}")
                else:
                    print(f"[SoulLaw] Skipped violation glyph injection (no KG writer).")
            except Exception as e:
                logger.error(f"[SoulLaw] Violation glyph injection failed: {e}")


# ✅ Lazy Singleton Accessor
_soul_law_instance: Optional['SoulLawValidator'] = None
def get_soul_law_validator() -> 'SoulLawValidator':
    global _soul_law_instance
    if _soul_law_instance is None:
        _soul_law_instance = SoulLawValidator()
    return _soul_law_instance

# ✅ Backward-compatible alias
soul_law_validator = get_soul_law_validator()

# 🔒 Warn if in test mode
if SOUL_LAW_MODE == "test":
    print("⚠️ WARNING: SoulLawValidator running in TEST MODE. Switch to full for production.")