"""
🧩 QKD Policy Enforcer — SRK-11 Task 2 (Tessaris Secure Layer)
Adaptive enforcement of QKD security, coherence, and GKey integrity policies.

This module forms the trust governor between:
 • GlyphWave transmission layer (GWIP/Photon)
 • Codex GKeyStore (quantum key repository)
 • SoulLaw trace engine (compliance and anomaly logging)

Validated under SRK-11 milestone — part of the Photon/Binary Bridge pipeline.
"""

from backend.modules.glyphwave.qkd_handshake import GKeyStore
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event
from backend.modules.glyphwave.qkd.qkd_errors import QKDPolicyViolationError


class QKDPolicyEnforcer:
    """
    🔒 QKDPolicyEnforcer — runtime verification of entanglement key integrity,
    coherence stability, and tamper detection before photon transmission.

    This ensures that all photon-exchange operations comply with active QKD policy
    and that only verified, entangled channels (GKeys) are utilized.
    """

    def __init__(self):
        # ✅ Use GKeyStore class reference directly (singleton pattern internally handled)
        self.gkey_store = GKeyStore

    # ────────────────────────────────────────────────────────────────
    def is_qkd_required(self, wave_packet: dict) -> bool:
        """
        Determine if QKD is explicitly required by this packet or its payload metadata.

        Args:
            wave_packet (dict): The glyphwave packet (GWIP or Photon capsule).

        Returns:
            bool: True if QKD policy requires verification.
        """
        metadata = wave_packet.get("qkd_policy", {})
        if not metadata:
            payload = wave_packet.get("payload", {})
            metadata = payload.get("qkd_policy", {})
        return metadata.get("require_qkd", False)

    # ────────────────────────────────────────────────────────────────
    def has_valid_gkey(self, sender_id: str, recipient_id: str) -> bool:
        """
        Verify that a valid, verified GKey exists between the sender and recipient.

        Returns:
            bool: True if a verified entanglement key pair exists.
        """
        gkey = self.gkey_store.get_key_pair(sender_id, recipient_id)
        return gkey is not None and gkey.get("status") == "verified"

    # ────────────────────────────────────────────────────────────────
    def enforce_policy(self, wave_packet: dict) -> bool:
        """
        Enforce active QKD policy.

        Allows photon propagation if:
         - QKD not required, OR
         - Valid verified GKey exists, AND
         - No tampering is detected.

        Returns:
            bool: True if policy passes; False otherwise.
        """
        sender_id = wave_packet.get("sender_id")
        recipient_id = wave_packet.get("recipient_id")

        if not self.is_qkd_required(wave_packet):
            return True  # ✅ No QKD required

        if not self.has_valid_gkey(sender_id, recipient_id):
            self._log_violation(wave_packet, "Missing or invalid GKey")
            return False

        if self.gkey_store.detect_tampering(sender_id, recipient_id):
            self._log_violation(wave_packet, "GKey tampering detected")
            return False

        return True  # ✅ All checks passed

    # ────────────────────────────────────────────────────────────────
    def _log_violation(self, wave_packet: dict, reason: str):
        """
        Log a QKD violation into the SoulLaw event trace for forensic tracking.

        Args:
            wave_packet (dict): Offending packet.
            reason (str): Reason for policy rejection.
        """
        log_soullaw_event(
            {
                "type": "qkd_policy_violation",
                "sender_id": wave_packet.get("sender_id"),
                "recipient_id": wave_packet.get("recipient_id"),
                "wave_id": wave_packet.get("wave_id"),
                "reason": reason,
            },
            glyph=None  # valid legacy arg for SoulLaw traces
        )

    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def enforce_if_required(context: dict):
        """
        Lightweight enforcement for Codex runtime contexts.
        Raises QKDPolicyViolationError if enforcement fails.

        Args:
            context (dict): Execution context containing sender, recipient, and qkd_policy.
        """
        from backend.modules.glyphwave.qkd_handshake import GKeyStore
        from backend.modules.glyphwave.qkd.qkd_errors import QKDPolicyViolationError

        sender_id = context.get("sender_id")
        recipient_id = context.get("recipient_id")
        qkd_policy = context.get("qkd_policy", {})

        if not qkd_policy.get("require_qkd"):
            return  # ✅ No enforcement needed

        gkey = GKeyStore.get_key_pair(sender_id, recipient_id)
        if not gkey or gkey.get("status") != "verified":
            raise QKDPolicyViolationError(f"Missing or invalid GKey for {sender_id} → {recipient_id}")

        if GKeyStore.detect_tampering(sender_id, recipient_id):
            raise QKDPolicyViolationError(f"GKey tampering detected for {sender_id} → {recipient_id}")