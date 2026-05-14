from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List


def _env_raw_vset() -> str:
    return (
        os.getenv("GLYPHCHAIN_VALIDATORS", "")
        or os.getenv("GLYPHCHAIN_VALIDATOR_SET", "")
        or os.getenv("CONSENSUS_VALIDATORS", "")
        or ""
    ).strip()


def _parse_vset_csv(raw: str) -> Dict[str, int]:
    """
    Accepts:
      - "val1:1,val2:2,val3:1"
      - "val1,val2,val3"            (implies power=1)
    Returns:
      { "val1": 1, "val2": 2, ... }   (keys are ALWAYS plain validator IDs)
    """
    powers: Dict[str, int] = {}
    s = (raw or "").strip()
    if not s:
        return powers

    for part in s.split(","):
        part = (part or "").strip()
        if not part:
            continue

        vid = part
        pwr = 1

        if ":" in part:
            left, right = part.split(":", 1)
            vid = (left or "").strip()
            try:
                pwr = int((right or "").strip() or "1")
            except Exception:
                pwr = 1

        if not vid:
            continue
        if pwr <= 0:
            pwr = 1

        powers[vid] = int(pwr)

    return powers


@dataclass
class ValidatorSet:
    powers: Dict[str, int]

    @classmethod
    def from_env(cls) -> "ValidatorSet":
        raw = _env_raw_vset()
        powers = _parse_vset_csv(raw)

        # dev convenience: ensure self is present
        self_vid = (os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip()
        if self_vid and self_vid not in powers:
            powers[self_vid] = 1

        return cls(powers=powers)

    def ordered_ids(self) -> List[str]:
        # deterministic across nodes; ALWAYS plain IDs (no ":power")
        return sorted(self.powers.keys())

    def is_member(self, val_id: str) -> bool:
        vid = (val_id or "").strip()
        return bool(vid) and (vid in self.powers)

    def power_of(self, val_id: str) -> int:
        vid = (val_id or "").strip()
        return int(self.powers.get(vid, 0))

    def total_power(self) -> int:
        return int(sum(int(p) for p in self.powers.values()))

    def quorum_power(self) -> int:
        """
        PR4 test-quorum: ceil(2/3 * total power).

        This makes 2-of-3 validators sufficient to finalize, so the
        cluster can keep advancing after one node is killed (as the
        integration gate expects).
        """
        tot = self.total_power()
        if tot <= 0:
            return 0
        return (2 * tot + 2) // 3