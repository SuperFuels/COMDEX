# backend/replay/reducer.py
from typing import Dict, Any, List

class ReplayReducer:
    """
    Deterministic state reducer for timeline replay.
    Applies replay frames to AtomSheets / workspace state.
    """

    @staticmethod
    def apply_state(base: Dict[str, Any], frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        state = base.copy()

        for frame in frames:
            for key, value in frame.items():
                # override
                if isinstance(value, (str, int, float, bool, type(None))):
                    state[key] = value
                    continue

                # merge dicts shallowly
                if isinstance(value, dict):
                    prev = state.get(key, {})
                    if isinstance(prev, dict):
                        merged = prev.copy()
                        merged.update(value)
                        state[key] = merged
                    else:
                        state[key] = value
                    continue

                # extend lists
                if isinstance(value, list):
                    prev = state.get(key, [])
                    if isinstance(prev, list):
                        state[key] = prev + value
                    else:
                        state[key] = value
                    continue

        return state