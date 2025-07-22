# backend/modules/sqi/qbit_format.py

from typing import Dict, Union, List

class QBitFormat:
    """
    Defines the symbolic representation of a QBit (Q-Glyph) in Codex SQI system.
    Supports formats like 'A:0 ↔ 1', entangled states, and contextual decoding.
    """

    def __init__(self):
        self.valid_states = ["0", "1"]

    def encode_qbit(self, base: str, states: Union[List[str], str]) -> Dict[str, Union[str, List[str]]]:
        """
        Encode a symbolic QBit from base and states.
        Example: encode_qbit("A", ["0", "1"]) → {'↔': ['A:0', 'A:1']}
        """
        if isinstance(states, str):
            states = states.split("↔")

        return {
            "↔": [f"{base}:{s.strip()}" for s in states if s.strip() in self.valid_states]
        }

    def decode_qbit(self, qbit: Dict[str, List[str]]) -> Dict[str, str]:
        """
        Decode a QBit into its base and symbolic states.
        """
        parts = qbit.get("↔", [])
        if not parts or len(parts) < 2:
            return {"error": "Invalid QBit"}

        base = parts[0].split(":")[0]
        return {
            "base": base,
            "state_0": parts[0],
            "state_1": parts[1],
        }

    def is_valid_qbit(self, qbit: Dict[str, List[str]]) -> bool:
        """
        Check if QBit follows proper dual-state symbolic format.
        """
        parts = qbit.get("↔", [])
        return (
            len(parts) == 2 and
            all(":" in p and p.split(":")[1] in self.valid_states for p in parts)
        )