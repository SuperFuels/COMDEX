"""
🔐 QKD Manager — GlyphWave Quantum Key Distribution Layer
Provides a unified interface for retrieving active QKD keys
and managing handshake lifecycle for vault synchronization.

Part of SRK-13 D7 (GlyphVault ↔ QKD Harmonization).
"""

import time
from backend.modules.glyphwave.qkd_handshake import QKDHandshake
from backend.modules.glyphwave.qkd.qkd_logger import log_qkd_event


class QKDManager:
    """Central access point for current QKD session keys."""

    def __init__(self):
        self._active_key = None
        self._timestamp = None

    def initiate_handshake(self):
        """Perform a QKD handshake and store the resulting key."""
        handshake = QKDHandshake()
        self._active_key = handshake.generate_session_key()
        self._timestamp = time.time()
        log_qkd_event("handshake_initiated", {"timestamp": self._timestamp})
        return self._active_key

    def get_active_key(self) -> str:
        """Return the active QKD key, refreshing if expired or missing."""
        if not self._active_key or (time.time() - (self._timestamp or 0)) > 3600:
            self.initiate_handshake()
        return self._active_key

    def refresh_key(self):
        """Force a fresh handshake and key rotation."""
        return self.initiate_handshake()