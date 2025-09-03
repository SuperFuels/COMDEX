# File: backend/modules/DreamOS/ghost_entry.py

import json
import os
from datetime import datetime
from typing import Optional

from backend.modules.glyphvault.waveglyph_signer import verify_waveglyph_signature
from backend.modules.encryption.glyph_vault import GlyphVault

GHOST_LOG_PATH = "containers/dreamos_ghosts/"  # Folder for ghost entries


def inject_ghost_from_gwv(trace_str: str, container_id: str) -> str:
    """
    Injects a symbolic ghost entry into a DreamOS container from a signed .gwv trace.
    Verifies Vault signature before accepting.
    Returns ghost entry filepath, or "" if verification fails.
    """
    try:
        trace_obj = json.loads(trace_str)

        # ✅ Verify signature before accepting
        public_key = GlyphVault().get_public_key()
        if not public_key:
            print("[DREAMOS] ❌ No Vault public key available — rejecting ghost trace.")
            return ""

        if not verify_waveglyph_signature(trace_obj, public_key):
            print("[DREAMOS] 🚫 Invalid signature — ghost trace rejected.")
            return ""

        # 🔍 Capture signed_by before stripping
        signed_by = trace_obj.get("signature_block", {}).get("signed_by", "unknown")

        # Strip signature block before saving ghost
        trace_obj.pop("signature_block", None)

        ghost_entry = {
            "type": "ghost_replay",
            "injected_at": datetime.utcnow().isoformat() + "Z",
            "source_container": container_id,
            "trace": trace_obj,
            "status": "latent",  # could be "active" if DreamOS activates it
            "verified_by": signed_by,
        }

        os.makedirs(GHOST_LOG_PATH, exist_ok=True)
        ghost_file = os.path.join(
            GHOST_LOG_PATH,
            f"{container_id}_ghost_{int(datetime.utcnow().timestamp())}.json"
        )

        with open(ghost_file, "w", encoding="utf-8") as f:
            json.dump(ghost_entry, f, indent=2)

        print(f"[DREAMOS] 👻 Ghost entry saved: {ghost_file} (signed_by: {signed_by})")
        return ghost_file

    except Exception as e:
        print(f"[DREAMOS] ⚠️ Failed to inject ghost entry: {e}")
        return ""