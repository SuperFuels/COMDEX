from backend.modules.glyphwave.qkd_handshake import GKeyStore
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event


class QKDPolicyEnforcer:
    def __init__(self):
        # ✅ Use class reference directly — no .get_instance() needed
        self.gkey_store = GKeyStore

    def is_qkd_required(self, wave_packet: dict) -> bool:
        metadata = wave_packet.get("qkd_policy", {})
        return metadata.get("require_qkd", False)

    def has_valid_gkey(self, sender_id: str, recipient_id: str) -> bool:
        gkey = self.gkey_store.get_key_pair(sender_id, recipient_id)
        return gkey is not None and gkey.get("status") == "verified"

    def enforce_policy(self, wave_packet: dict) -> bool:
        sender_id = wave_packet.get("sender_id")
        recipient_id = wave_packet.get("recipient_id")

        if not self.is_qkd_required(wave_packet):
            return True  # No enforcement needed

        if self.has_valid_gkey(sender_id, recipient_id):
            return True  # Valid GKey in place

        # 🚨 Log QKD failure with dummy glyph
        log_soullaw_event({
            "type": "qkd_policy_violation",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "wave_id": wave_packet.get("wave_id"),
            "reason": "Missing or invalid GKey during QKD-required transmission",
        }, glyph="qkd_violation")

        return False  # ❌ Block transmission