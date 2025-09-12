# File: backend/modules/glyphwave/security/symbolic_qkd_locker.py

import hashlib
import time
from typing import Optional, Dict, Any

from backend.modules.glyphvault.soul_law_validator import SoulLawValidator
from backend.modules.codex.codex_executor import execute_codex
from backend.modules.glyphwave.core.wave_state import WaveState


class SymbolicQKDLocker:
    """
    Symbolic Quantum Key Distribution (QKD) Locking system.

    Uses symbolic parameters, container state, CodexLang hashes,
    and SoulLaw intent to validate access to beams, containers, or predictions.
    """

    def __init__(self):
        self.validator = SoulLawValidator()

    def _generate_qkd_hash(self, wave: WaveState, identity: str) -> str:
        """
        Derives a unique symbolic QKD hash based on wave properties and identity.
        """
        base = f"{wave.id}|{identity}|{wave.phase}|{wave.amplitude}|{wave.coherence}|{int(wave.timestamp)}"
        return hashlib.sha256(base.encode()).hexdigest()

    def validate_access(
        self,
        wave: WaveState,
        identity: str,
        container: Optional[Dict[str, Any]] = None,
        intent_codex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validates symbolic access to a wave or container.

        Returns:
            {
                "valid": bool,
                "reason": str,
                "qkd_hash": str,
                "codex_result": Optional[dict],
                "soul_check": Optional[dict]
            }
        """
        qkd_hash = self._generate_qkd_hash(wave, identity)

        # Step 1: SoulLaw Check (if container present)
        soul_check = {"valid": True, "reason": "no container"}
        if container:
            soul_check = self.validator.validate_container(container)

        # Step 2: CodexLang intent evaluation (if codex provided)
        codex_result = None
        if intent_codex:
            try:
                codex_result = execute_codex(intent_codex)
                if codex_result.get("status") == "contradiction":
                    return {
                        "valid": False,
                        "reason": "Intent contradiction",
                        "qkd_hash": qkd_hash,
                        "codex_result": codex_result,
                        "soul_check": soul_check,
                    }
            except Exception as e:
                return {
                    "valid": False,
                    "reason": f"CodexLang error: {str(e)}",
                    "qkd_hash": qkd_hash,
                    "codex_result": None,
                    "soul_check": soul_check,
                }

        # Final validity
        if not soul_check.get("valid", True):
            return {
                "valid": False,
                "reason": f"SoulLaw rejected: {soul_check.get('reason')}",
                "qkd_hash": qkd_hash,
                "codex_result": codex_result,
                "soul_check": soul_check,
            }

        return {
            "valid": True,
            "reason": "Access granted",
            "qkd_hash": qkd_hash,
            "codex_result": codex_result,
            "soul_check": soul_check,
        }