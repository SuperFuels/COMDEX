from backend.modules.glyphwave.qkd_handshake import GKeyStore
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event
from backend.modules.glyphwave.qkd.qkd_errors import QKDPolicyViolationError


class QKDPolicyEnforcer:
    def __init__(self):
        # ✅ Use class reference directly — no .get_instance() needed
        self.gkey_store = GKeyStore

    def is_qkd_required(self, wave_packet: dict) -> bool:
        """
        Check if QKD is explicitly required by the wave_packet or its payload.
        """
        metadata = wave_packet.get("qkd_policy", {})
        if not metadata:
            payload = wave_packet.get("payload", {})
            metadata = payload.get("qkd_policy", {})
        return metadata.get("require_qkd", False)

    def has_valid_gkey(self, sender_id: str, recipient_id: str) -> bool:
        """
        Verify that a valid, verified GKey exists between sender and recipient.
        """
        gkey = self.gkey_store.get_key_pair(sender_id, recipient_id)
        return gkey is not None and gkey.get("status") == "verified"

    def enforce_policy(self, wave_packet: dict) -> bool:
        """
        Main enforcement logic. Allows wave if:
        - QKD not required
        - Valid GKey exists
        - No tampering detected
        """
        sender_id = wave_packet.get("sender_id")
        recipient_id = wave_packet.get("recipient_id")

        if not self.is_qkd_required(wave_packet):
            return True  # No enforcement needed

        if not self.has_valid_gkey(sender_id, recipient_id):
            self._log_violation(wave_packet, "Missing or invalid GKey")
            return False

        if self.gkey_store.detect_tampering(sender_id, recipient_id):
            self._log_violation(wave_packet, "GKey tampering detected")
            return False

        return True  # ✅ All checks passed

    def _log_violation(self, wave_packet: dict, reason: str):
        """
        Log the QKD violation to the SoulLaw event trace.
        """
        log_soullaw_event(
            {
                "type": "qkd_policy_violation",
                "sender_id": wave_packet.get("sender_id"),
                "recipient_id": wave_packet.get("recipient_id"),
                "wave_id": wave_packet.get("wave_id"),
                "reason": reason,
            },
            glyph=None  # Still valid as second arg
        )

    @staticmethod
    def enforce_if_required(context: dict):
        """
        Enforce QKD policy from a Codex execution context.
        Raises QKDPolicyViolationError if enforcement fails.
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