# File: backend/modules/soullaw/intercept_measurements.py

import logging
from typing import Dict, Any, Optional, Union
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
from backend.modules.symbolic.symbol_tree_generator import SymbolicMeaningTree 

logger = logging.getLogger("soul_measurement")

class SoulLawMeasurementInterceptor:
    def __init__(self):
        self.validator = get_soul_law_validator()

    def intercept_symbolic_measurement(
        self,
        tree: SymbolicMeaningTree,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Evaluate a symbolic meaning tree before collapse or measurement.
        Returns True if allowed, False if blocked by SoulLaw.
        """
        logger.info("[🔍] Intercepting symbolic tree measurement for SoulLaw compliance")
        violations = self.validator.apply_soullaw_gating(tree)

        if any(v.get("status") == "blocked" for v in violations.values()):
            logger.warning("[🛑] SoulLaw blocked symbolic collapse due to violations.")
            return False

        logger.info("[✅] Symbolic tree approved for measurement/collapse.")
        return True

    def intercept_qglyph_payload(
        self,
        glyph: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Evaluate a QGlyph payload before executing a symbolic collapse.
        Returns True if allowed, False if blocked.
        """
        metadata = metadata or {}
        glyph_str = str(glyph).lower()

        # Optional: reject harmful patterns
        if "collapse_all" in glyph_str or "destructive" in glyph_str:
            self.validator._inject_violation(
                "destructive_intent", "Detected dangerous collapse trigger"
            )
            logger.error("[🛑] Collapse rejected: Destructive intent detected")
            return False

        # Evaluate via SoulLaw ethics
        if not self.validator.evaluate_ethics_solo(glyph_str):
            self.validator._inject_violation(
                "ethical_violation", "Glyph failed SoulLaw ethics validation"
            )
            return False

        self.validator._inject_approval(
            "symbolic_measurement", "QGlyph payload approved"
        )
        return True


# Lazy Singleton
_soul_interceptor: Optional[SoulLawMeasurementInterceptor] = None

def get_measurement_interceptor() -> SoulLawMeasurementInterceptor:
    global _soul_interceptor
    if _soul_interceptor is None:
        _soul_interceptor = SoulLawMeasurementInterceptor()
    return _soul_interceptor