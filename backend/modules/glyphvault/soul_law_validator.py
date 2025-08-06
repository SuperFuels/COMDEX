# File: backend/modules/glyphvault/soul_law_validator.py

import os
import logging
import hashlib
import importlib
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# 🌐 Mode detection: full or test (fallback)
SOUL_LAW_MODE = os.getenv("SOUL_LAW_MODE", "full").lower()

def inject_approval_glyph(payload: Dict):
    """
    Injects an approval glyph into the GlyphNet WebSocket stream.
    Uses a lazy import for broadcast_event to avoid circular import chains.
    """
    try:
        from backend.routes.ws.glyphnet_ws import broadcast_event  # ✅ Lazy import to break circular import
        broadcast_event(payload)
        logger.info(f"[SoulLaw] Approval glyph broadcasted: {payload}")
    except Exception as e:
        logger.error(f"[SoulLaw] Approval glyph injection failed: {e}")


# Existing or placeholder functions remain here (no changes to their logic):
def get_soul_law_validator():
    """
    Dynamically imports and returns the SoulLawValidator.
    Uses importlib to avoid premature circular imports.
    """
    module = importlib.import_module("backend.modules.glyphvault.soul_law_core")
    return getattr(module, "SoulLawValidator")()

# ✅ Safe import for broadcast_event
try:
    from backend.modules.glyphnet.glyphnet_ws import broadcast_event
except ImportError:
    def broadcast_event(event_type: str, payload: dict):
        print(f"[SIM:FALLBACK] Broadcast: {event_type} → {payload}")


def _lazy_load_kg_writer():
    """Lazy loader for KnowledgeGraphWriter to avoid circular imports."""
    try:
        kg_module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")
        return kg_module.KnowledgeGraphWriter
    except ImportError as e:
        logger.warning(f"[SoulLaw] Failed to import KnowledgeGraphWriter: {e}")
        # ✅ Fallback: Return a stub class that avoids binding errors
        class StubKGWriter:
            def inject_glyph(self, *args, **kwargs):
                print(f"[SIM:FALLBACK] Glyph inject: {kwargs.get('metadata', {}).get('rule', 'unknown')}")
        return StubKGWriter


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
            self.kg_writer = kg_class_or_stub() if callable(kg_class_or_stub) else kg_class_or_stub
        return self.kg_writer

    def validate_avatar(self, avatar_state: Optional[Dict]) -> bool:
        """Check if avatar meets SoulLaw level and morality gates."""
        if SOUL_LAW_MODE == "test":
            logger.debug("[SoulLaw] SAFE MODE: Auto-approving avatar validation.")
            self._inject_approval("safe_mode_bypass", "Avatar auto-approved in SAFE MODE")
            return True

        if not avatar_state:
            logger.debug("[SoulLaw] Avatar state missing")
            self._inject_violation("missing_avatar_state", "No avatar state provided")
            return False

        if "id" not in avatar_state or "role" not in avatar_state:
            logger.debug("[SoulLaw] Avatar state missing required fields (id/role)")
            self._inject_violation("incomplete_avatar_state", "Avatar missing id or role")
            return False

        level = avatar_state.get("level", 0)
        if level < self.MIN_AVATAR_LEVEL:
            logger.debug(f"[SoulLaw] Avatar level {level} below minimum {self.MIN_AVATAR_LEVEL}")
            self._inject_violation("low_level", f"Avatar level {level} below required {self.MIN_AVATAR_LEVEL}")
            return False

        self._inject_approval("avatar_approval", f"Avatar level {level} approved")
        return True

    def validate_avatar_with_context(self, avatar_state: Optional[Dict], context: Optional[dict] = None) -> bool:
        """
        Extended avatar validation for hyperdrive or container contexts.
        Accepts either dict context (preferred) or string fallback.
        """
        # If context is incorrectly passed as a string, log and bypass safely
        if context and not isinstance(context, dict):
            logger.warning(f"[SoulLaw] Non-dict context passed ({type(context)}). Converting to dict fallback.")
            context = {"raw_context": str(context)}

        logger.debug(f"[SoulLaw] Context-aware validation invoked. Context: {context}")

        # Context override: safe hyperdrive mode
        if context and context.get("hyperdrive_mode") == "safe":
            self._inject_approval("hyperdrive_safe_mode", "Context override: safe hyperdrive mode")
            return True

        return self.validate_avatar(avatar_state)

    def validate_avatar_state(self, avatar_state: Optional[Dict]) -> bool:
        """Alias for validate_avatar for backward compatibility."""
        return self.validate_avatar(avatar_state)

    def validate_container(self, container_metadata: Optional[Dict]) -> bool:
        """Validate container morality gates (expandable for trait checks)."""
        if SOUL_LAW_MODE == "test":
            logger.debug("[SoulLaw] SAFE MODE: Auto-approving container validation.")
            self._inject_approval("safe_mode_bypass_container", "Container auto-approved in SAFE MODE")
            return True

        if not container_metadata or "id" not in container_metadata:
            self._inject_violation("invalid_container_metadata", "Container metadata incomplete")
            return False

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
                kg_writer.inject_glyph(
                    content=reason,
                    glyph_type="approval",
                    metadata={"rule": rule, "type": "SoulLaw", "origin": "SoulLawValidator", "tags": ["📜", "🧠", "✅"]},
                    plugin="SoulLaw"
                )
                broadcast_event("soul_law_update", {"rule": rule, "status": "approval", "reason": reason})
                print(f"✅ [SoulLaw] Approval: {rule} – {reason}")
            except Exception as e:
                logger.error(f"[SoulLaw] Approval glyph injection failed: {e}")

    def _inject_violation(self, rule: str, reason: str):
        if self.enable_glyph_injection:
            try:
                kg_writer = self._get_kg_writer()
                kg_writer.inject_glyph(
                    content=reason,
                    glyph_type="violation",
                    metadata={"rule": rule, "type": "SoulLaw", "origin": "SoulLawValidator", "tags": ["📜", "🧠", "❌"]},
                    plugin="SoulLaw"
                )
                broadcast_event("soul_law_update", {"rule": rule, "status": "violation", "reason": reason})
                print(f"❌ [SoulLaw] Violation: {rule} – {reason}")
            except Exception as e:
                logger.error(f"[SoulLaw] Violation glyph injection failed: {e}")

    def filter_unethical_feedback(self, feedback: dict) -> dict:
        """
        Filters or flags unethical elements in feedback for safe usage.
        """
        if not isinstance(feedback, dict):
            raise ValueError("Feedback must be a dict.")

        unethical_flags = feedback.get("unethical_flags", [])
        if unethical_flags:
            feedback["status"] = "flagged"
            feedback["notes"] = feedback.get("notes", "") + " | ⚠️ SoulLaw flagged unethical content."
            feedback.pop("dangerous_logic", None)
            self._inject_violation("unethical_feedback", "Feedback contained flagged unethical elements")
        else:
            self._inject_approval("ethical_feedback", "Feedback passed SoulLaw compliance")

        return feedback


# ✅ Lazy Singleton Accessor
_soul_law_instance: Optional['SoulLawValidator'] = None
def get_soul_law_validator() -> 'SoulLawValidator':
    global _soul_law_instance
    if _soul_law_instance is None:
        _soul_law_instance = SoulLawValidator()
    return _soul_law_instance

# ✅ Backward-compatible alias
soul_law_validator = get_soul_law_validator()

# ✅ NEW: Top-level alias for direct import compatibility
def filter_unethical_feedback(feedback: dict) -> dict:
    return get_soul_law_validator().filter_unethical_feedback(feedback)

# 🔒 Warn if in test mode
if SOUL_LAW_MODE == "test":
    print("⚠️ WARNING: SoulLawValidator running in TEST MODE. Switch to full for production.")