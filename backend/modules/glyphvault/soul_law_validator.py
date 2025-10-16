# File: backend/modules/glyphvault/soul_law_validator.py

import os
import time
import logging
import hashlib
import importlib
from typing import Optional, Dict, Any
from backend.modules.soul.soul_laws import enforce_soul_laws
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event

logger = logging.getLogger(__name__)

# 🌐 Mode detection: "full" (default) or "test"
SOUL_LAW_MODE = os.getenv("SOUL_LAW_MODE", "full").lower()

# --------------------------------------------------------------------------------------
# 🔊 Broadcasting (prefer throttled WS broadcast; safe fallback in offline/test contexts)
# --------------------------------------------------------------------------------------
try:
    # Prefer throttled broadcast to avoid loop storms
    from backend.modules.glyphnet.glyphnet_ws import broadcast_event_throttled as broadcast_event  # type: ignore
except Exception:
    def broadcast_event(event_type: str, payload: dict):
        print(f"[SIM:FALLBACK] Broadcast: {event_type} → {payload}")

# Minimal local throttle guard (belt & suspenders; still useful if throttled import fails)
_MIN_EMIT_INTERVAL = float(os.getenv("SOULLAW_MIN_EMIT_INTERVAL", "0.75"))
_last_emit: Dict[str, float] = {}


def inject_approval_glyph(payload: Dict[str, Any]):
    """
    Injects an approval glyph into the GlyphNet WebSocket stream.
    Uses a lazy import for broadcast_event to avoid circular import chains.
    """
    try:
        # If your routes layer exposes a broadcaster, this path remains compatible.
        from backend.routes.ws.glyphnet_ws import broadcast_event as route_broadcast  # type: ignore
        route_broadcast(payload)
        logger.info(f"[SoulLaw] Approval glyph broadcasted: {payload}")
    except Exception as e:
        logger.error(f"[SoulLaw] Approval glyph injection failed: {e}")


# --------------------------------------------------------------------------------------
# 📦 Optional: dynamic access to the *core* validator (kept for backward compatibility)
# --------------------------------------------------------------------------------------
def get_soul_law_core_validator():
    """
    Dynamically imports and returns SoulLawValidator from soul_law_core (if you use that).
    Uses importlib to avoid premature circular imports.
    """
    module = importlib.import_module("backend.modules.glyphvault.soul_law_core")
    return getattr(module, "SoulLawValidator")()


# --------------------------------------------------------------------------------------
# 🧠 Knowledge Graph writer (lazy import with a safe stub fallback)
# --------------------------------------------------------------------------------------
def _lazy_load_kg_writer():
    """Lazy loader for KnowledgeGraphWriter to avoid circular imports."""
    try:
        kg_module = importlib.import_module("backend.modules.knowledge_graph.knowledge_graph_writer")
        return kg_module.KnowledgeGraphWriter
    except ImportError as e:
        logger.warning(f"[SoulLaw] Failed to import KnowledgeGraphWriter: {e}")

        class StubKGWriter:
            def inject_glyph(self, *args, **kwargs):
                print(f"[SIM:FALLBACK] Glyph inject: {kwargs.get('metadata', {}).get('rule', 'unknown')}")

        return StubKGWriter


# ✅ Test mode stub (kept for explicit clarity)
if SOUL_LAW_MODE != "full":
    class KnowledgeGraphWriter:
        def inject_glyph(self, *args, **kwargs):
            print(f"[SIM] SoulLaw glyph (test mode): {kwargs.get('metadata', {}).get('rule', 'unknown')}")
    print("⚠️ SoulLaw running in TEST MODE: Using stubbed KnowledgeGraphWriter")


class SoulLawValidator:
    COOL_DOWN = float(os.getenv("SOULLAW_COOLDOWN_SEC", "30.0"))  # seconds
    """Validates avatar states and containers against immutable Soul Laws."""

    MIN_AVATAR_LEVEL = 10  # Example threshold

    def __init__(self):
        self.soul_laws = {"value_of_life": True, "do_no_harm": True}
        self.kg_writer = None  # Lazy init
        self.enable_glyph_injection = True

    # -----------------------
    # 🔁 Internal utilities
    # -----------------------
    def _get_kg_writer(self):
        """Initialize KnowledgeGraphWriter lazily."""
        if self.kg_writer is None:
            kg_class_or_stub = _lazy_load_kg_writer()
            self.kg_writer = kg_class_or_stub() if callable(kg_class_or_stub) else kg_class_or_stub
        return self.kg_writer

    def _emit(self, event_type: str, payload: dict, key: str, min_interval: float = _MIN_EMIT_INTERVAL):
        """
        Emit with a simple per-key throttle (works even if throttled import isn't available).
        """
        now = time.time()
        last = _last_emit.get(key, 0.0)
        if now - last < max(min_interval, 0.0):
            return
        _last_emit[key] = now
        try:
            broadcast_event(event_type, payload)
        except Exception as e:
            logger.debug(f"[SoulLaw] Broadcast failed (non-fatal): {e}")

    # -----------------------
    # ✅ Avatar validation
    # -----------------------
    def validate_avatar(self, avatar_state: Optional[Dict[str, Any]]) -> bool:
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

    def validate_avatar_with_context(self, avatar_state: Optional[Dict[str, Any]], context: Optional[dict] = None) -> bool:
        """
        Extended avatar validation for hyperdrive or container contexts.
        Accepts either dict context (preferred) or string fallback.
        """
        if context and not isinstance(context, dict):
            logger.warning(f"[SoulLaw] Non-dict context passed ({type(context)}). Converting to dict fallback.")
            context = {"raw_context": str(context)}

        logger.debug(f"[SoulLaw] Context-aware validation invoked. Context: {context}")

        # Context override: safe hyperdrive mode
        if context and context.get("hyperdrive_mode") == "safe":
            self._inject_approval("hyperdrive_safe_mode", "Context override: safe hyperdrive mode")
            return True

        return self.validate_avatar(avatar_state)

    def validate_avatar_state(self, avatar_state: Optional[Dict[str, Any]]) -> bool:
        """Alias for validate_avatar for backward compatibility."""
        return self.validate_avatar(avatar_state)

    # -----------------------
    # 📦 Container validation
    # -----------------------
    def validate_container(self, container_metadata: Optional[Dict]) -> bool:
        if SOUL_LAW_MODE == "test":
            self._inject_approval("safe_mode_bypass_container", "Container auto-approved in SAFE MODE")
            return True

        if not container_metadata or "id" not in container_metadata:
            self._inject_violation("invalid_container_metadata", "Container metadata incomplete")
            return False

        cid = container_metadata["id"]
        now = time.time()
        last = self._container_approval_cache.get(cid, 0)
        if now - last < self.COOL_DOWN:
            # Already approved recently; skip re-broadcast
            return True

        self._inject_approval("container_ok", "Container passed moral validation")
        self._container_approval_cache[cid] = now
        return True

    @staticmethod
    def validate_navigation_link(
        source_container: dict,
        target_container: dict,
        link_metadata: Optional[dict] = None
    ):
        """Block forbidden container links (e.g., secure → public), unless long-range quantum/optical override applies."""
        source_tags = source_container.get("tags", [])
        target_tags = target_container.get("tags", [])

        if "secure" in source_tags and "public" in target_tags:
            # 🛡️ SoulLaw Override for Long-Range Links
            if link_metadata:
                carrier = link_metadata.get("carrier_type", "").upper()
                intent = link_metadata.get("intent", "").lower()
                distance = link_metadata.get("distance_km", 0)
                override_flag = link_metadata.get("soul_law_override", False)

                if (
                    carrier in ("QUANTUM", "OPTICAL") and
                    (intent == "long_range" or distance >= 1000 or override_flag is True)
                ):
                    print(f"⚠️ SoulLaw override: secure→public allowed via long-range {carrier} link ({distance}km)")
                    return  # ✅ Override allowed

            raise PermissionError("❌ SoulLaw: Secure container cannot link to public.")

        print(f"✅ SoulLaw: Navigation link allowed {source_container.get('id', '?')} → {target_container.get('id', '?')}")

    # -----------------------
    # 🔐 Seed locks
    # -----------------------
    def generate_seed_lock(self, identity: str, entropy: str) -> str:
        return hashlib.sha256(f"{identity}:{entropy}".encode("utf-8")).hexdigest()

    def verify_seed_lock(self, key: str, expected_hash: str) -> bool:
        if key != expected_hash:
            logger.warning("[SoulLaw] Seed-lock mismatch detected")
            self._inject_violation("seed_lock_mismatch", "Key mismatch")
            return False
        self._inject_approval("seed_lock_validated", "Seed lock key matched")
        return True

    # -----------------------
    # 🟩/🟥 Emit helpers
    # -----------------------
    def _inject_approval(self, rule: str, reason: str):
        if not self.enable_glyph_injection:
            return
        try:
            kg_writer = self._get_kg_writer()
            kg_writer.inject_glyph(
                content=reason,
                glyph_type="approval",
                metadata={
                    "rule": rule,
                    "type": "SoulLaw",
                    "origin": "SoulLawValidator",
                    "tags": ["📜", "🧠", "✅"],
                },
                plugin="SoulLaw",
            )
            self._emit(
                "soul_law_update",
                {"rule": rule, "status": "approval", "reason": reason},
                key=f"approval:{rule}",
            )
            print(f"✅ [SoulLaw] Approval: {rule} – {reason}")
        except Exception as e:
            logger.error(f"[SoulLaw] Approval glyph injection failed: {e}")

    def _inject_violation(self, rule: str, reason: str):
        if not self.enable_glyph_injection:
            return
        try:
            kg_writer = self._get_kg_writer()
            kg_writer.inject_glyph(
                content=reason,
                glyph_type="violation",
                metadata={
                    "rule": rule,
                    "type": "SoulLaw",
                    "origin": "SoulLawValidator",
                    "tags": ["📜", "🧠", "❌"],
                },
                plugin="SoulLaw",
            )
            self._emit(
                "soul_law_update",
                {"rule": rule, "status": "violation", "reason": reason},
                key=f"violation:{rule}",
            )
            print(f"❌ [SoulLaw] Violation: {rule} – {reason}")
        except Exception as e:
            logger.error(f"[SoulLaw] Violation glyph injection failed: {e}")

    # -----------------------
    # ⚖️ Transition Veto Check (for Codex/QQC)
    # -----------------------
    @staticmethod
    def verify_transition(context: Optional[dict], codex_program: str) -> bool:
        """
        Evaluates whether a CodexLang symbolic transition is ethically permissible.
        Returns False to veto unsafe or unethical transitions.
        """
        try:
            # Simple placeholder — expand later using enforce_soul_laws()
            from backend.modules.soul.soul_laws import enforce_soul_laws

            # If context explicitly disables ethics (for tests), allow
            if context and context.get("override_ethics") is True:
                return True

            # If program contains delay/entanglement ops, run ethics enforcement
            if any(op in codex_program for op in ("⧖", "↔", "∇", "⟲")):
                if not enforce_soul_laws(action=codex_program, context=context or {}):
                    print(f"❌ [SoulLaw] Vetoed symbolic transition: {codex_program}")
                    return False

            return True

        except Exception as e:
            print(f"[SoulLaw] ⚠️ Error during verify_transition: {e}")
            return False

    # -----------------------
    # 🧹 Feedback filter
    # -----------------------
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

    def validate_beam_event(self, beam: dict) -> bool:
        """
        Validate a beam event against SoulLaw constraints.
        Returns True if allowed. Logs violations or approvals to KG + GlyphNet.
        """
        if not beam:
            raise ValueError("Empty beam event.")

        if not beam.get("source") or not beam.get("target"):
            raise ValueError("Missing source or target in beam.")

        try:
            violations = evaluate_soullaw_violations(beam)
            is_blocked = violations.get("blocked", False)
            violation_list = violations.get("violations", [])

            if is_blocked:
                reason = ", ".join(violation_list) or "unspecified violation"

                # 🟥 Log violation to KG + broadcast
                log_soullaw_event({
                    "event_type": "beam_violation",
                    "beam_id": beam.get("id"),
                    "container_id": beam.get("container_id"),
                    "violations": violation_list,
                    "source": beam.get("source"),
                    "target": beam.get("target"),
                    "timestamp": beam.get("timestamp"),
                })

                self._inject_violation("beam_violation", reason)
                return False

            else:
                # 🟩 Approval path
                self._inject_approval("beam_approved", "Beam passed SoulLaw check")
                return True

        except Exception as e:
            self._inject_violation("beam_validation_error", str(e))
            raise
# --------------------------------------------------------------------------------------
# 🔁 Lazy Singleton Accessor (public)
# --------------------------------------------------------------------------------------
def verify_transition(context: Optional[dict], codex_program: str) -> bool:
    """Convenience alias for global access from QQC/CodexFeedbackLoop."""
    return get_soul_law_validator().verify_transition(context, codex_program)

_soul_law_instance: Optional['SoulLawValidator'] = None

def get_soul_law_validator() -> 'SoulLawValidator':
    global _soul_law_instance
    if _soul_law_instance is None:
        _soul_law_instance = SoulLawValidator()
    return _soul_law_instance


# Backward-compatible alias
soul_law_validator = get_soul_law_validator()

# Direct function alias (legacy imports)
def filter_unethical_feedback(feedback: dict) -> dict:
    return get_soul_law_validator().filter_unethical_feedback(feedback)

# 🔒 Warn if in test mode
if SOUL_LAW_MODE == "test":
    print("⚠️ WARNING: SoulLawValidator running in TEST MODE. Switch to full for production.")