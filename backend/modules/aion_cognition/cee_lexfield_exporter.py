# ================================================================
# 🧠 CEE Language Path - LexField Resonance Exporter
# ================================================================
"""
Aggregates all lexical exercise generators into a unified resonance
map for the AION Learning Engine.

Inputs:
    - Generated exercises (matchup, anagram, unjumble, cloze, group_sort)
    - Resonance metadata (ρ, I, SQI) from each exercise

Output:
    data/learning/lexfield_<session>.qdata.json

Schema Example:
{
  "timestamp": ...,
  "session": "lexfield_v1",
  "entries": [
    {"type": "cloze", "prompt": "...", "ρ": 0.74, "I": 0.91, "SQI": 0.82},
    ...
  ],
  "averages": {"ρ̄": 0.76, "Ī": 0.89, "SQĪ": 0.83},
  "schema": "LexFieldQData.v1"
}
"""

import json, time, logging
from pathlib import Path

from backend.modules.aion_cognition.cee_language_templates import (
    generate_matchup, generate_anagram, generate_unjumble
)
from backend.modules.aion_cognition.cee_language_cloze import (
    generate_cloze, generate_group_sort
)

logger = logging.getLogger(__name__)
OUT_DIR = Path("data/learning")


class LexFieldExporter:
    """Collects and persists language resonance data."""

    def __init__(self, session_id="lexfield_v1"):
        self.session_id = session_id
        self.entries = []

    # ------------------------------------------------------------
    def collect(self):
        """Generate a full lexical set."""
        self.entries.extend([
            generate_matchup(),
            generate_anagram(),
            generate_unjumble(),
            generate_cloze("The sun is bright", "bright"),
            generate_group_sort({
                "Emotions": ["happy", "sad", "angry"],
                "Colors": ["red", "blue", "green"]
            })
        ])
        logger.info(f"[LexFieldExporter] Collected {len(self.entries)} lexical exercises.")

    # ------------------------------------------------------------
    def summarize(self):
        """Compute average resonance values."""
        if not self.entries:
            return {}
        rhos = [e["resonance"]["ρ"] for e in self.entries]
        intensities = [e["resonance"]["I"] for e in self.entries]
        sqis = [e["resonance"]["SQI"] for e in self.entries]
        return {
            "ρ̄": round(sum(rhos) / len(rhos), 3),
            "Ī": round(sum(intensities) / len(intensities), 3),
            "SQĪ": round(sum(sqis) / len(sqis), 3),
        }

    # ------------------------------------------------------------
    def export(self):
        """Write session to disk."""
        summary = self.summarize()
        packet = {
            "timestamp": time.time(),
            "session": self.session_id,
            "entries": self.entries,
            "averages": summary,
            "schema": "LexFieldQData.v1",
        }

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        outpath = OUT_DIR / f"{self.session_id}.qdata.json"
        json.dump(packet, open(outpath, "w"), indent=2)
        logger.info(f"[LexFieldExporter] Exported resonance map -> {outpath}")
        return outpath, packet


# ------------------------------------------------------------
# CLI Test
# ------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    exporter = LexFieldExporter()
    exporter.collect()
    outpath, packet = exporter.export()
    print(json.dumps(packet["averages"], indent=2))
    print("✅ LexField resonance export complete.")