from typing import Dict, Optional, List, Any
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.holograms.ghx_replay_broadcast import emit_gwave_replay


class WaveStateStore:
    """
    In-memory store of WaveState objects for GlyphWave.
    Tracks currently active symbolic waves, along with optional carrier metadata
    and cached CodexLang execution results.
    """

    def __init__(self):
        self._store: Dict[str, WaveState] = {}
        self._carrier_info: Dict[str, Dict[str, Any]] = {}
        self._cached_scores: Dict[str, Dict[str, Any]] = {}  # ✅ wave_id -> {sqi_score, prediction, collapse_state}

    def add_wave(self, wave: WaveState, carrier_type: Optional[str] = None, modulation: Optional[str] = None) -> None:
        """
        Adds or updates a wave by its origin ID, along with optional carrier metadata.
        Emits GHX replay for visual sync.
        """
        if not wave.id:
            raise ValueError("WaveState must have a unique `id` to be stored.")

        self._store[wave.id] = wave

        if carrier_type or modulation:
            self._carrier_info[wave.id] = {
                "carrier_type": carrier_type,
                "modulation": modulation,
            }

        emit_gwave_replay(wave)  # 🧠 Emits live trace to GHX visual system

    def get_wave(self, wave_id: str) -> Optional[WaveState]:
        return self._store.get(wave_id)

    def get_carrier_info(self, wave_id: str) -> Optional[Dict[str, Any]]:
        return self._carrier_info.get(wave_id)

    def remove_wave(self, wave_id: str) -> None:
        self._store.pop(wave_id, None)
        self._carrier_info.pop(wave_id, None)
        self._cached_scores.pop(wave_id, None)  # ✅ Ensure cached results are removed too

    def all_waves(self) -> List[WaveState]:
        return list(self._store.values())

    def clear(self) -> None:
        self._store.clear()
        self._carrier_info.clear()
        self._cached_scores.clear()  # ✅ Clear cache on reset

    def snapshot(self) -> Dict[str, dict]:
        """
        Export all wave states as dicts, including carrier info if present.
        """
        return {
            wid: {
                "wave": wave.to_dict(),
                "carrier": self._carrier_info.get(wid, {}),
                "cached": self._cached_scores.get(wid, {})  # ✅ Include cached scores in snapshot
            }
            for wid, wave in self._store.items()
        }

    # ✅ New: Caching logic for SQI results
    def cache_prediction(self, wave_id: str, sqi_score: float, collapse_state: str, prediction: Any) -> None:
        self._cached_scores[wave_id] = {
            "sqi_score": sqi_score,
            "collapse_state": collapse_state,
            "prediction": prediction
        }

    def get_cached_prediction(self, wave_id: str) -> Optional[Dict[str, Any]]:
        return self._cached_scores.get(wave_id)

# ────────────────────────────────────────────────────────────────
# ✅ Compatibility wrapper for QKD handshake imports
# Allows: from backend.modules.glyphwave.core.wave_state_store import store_wave_state

_wave_state_store = WaveStateStore()

def store_wave_state(wave):
    """
    Compatibility wrapper for backward modules (like qkd_crypto_handshake)
    that call store_wave_state(wave).
    Delegates to the singleton WaveStateStore instance.
    """
    try:
        _wave_state_store.add_wave(wave)
        return True
    except Exception as e:
        print(f"[WaveStateStore] ⚠️ Failed to store wave: {e}")
        return False