# backend/modules/glyphcore/action_context_builder.py

from typing import Optional, Dict

from backend.modules.glyphwave.qkd.gkey_encryptor import GKeyStore
from backend.modules.auth.user_context import get_user_role_by_id  # Example stub import
from backend.modules.glyphwave.gwave_entropy import get_entropy_by_wave_id  # Optional stub

def build_action_context(
    sender_id: str,
    recipient_id: str,
    wave_id: Optional[str] = None,
    trace_signature: Optional[str] = None,
) -> Dict:
    """
    Constructs a full action context dict for symbolic enforcement:
    - QKD pair data
    - Sender/recipient metadata
    - Optional entropy + trace info
    - User roles
    """

    qkd_pair = GKeyStore.get_key_pair(sender_id, recipient_id)
    user_role = get_user_role_by_id(sender_id) if sender_id else None
    entropy = get_entropy_by_wave_id(wave_id) if wave_id else None

    return {
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "wave_id": wave_id,
        "qkd_pair": qkd_pair,
        "user_role": user_role,
        "entropy": entropy,
        "trace_signature": trace_signature,
    }