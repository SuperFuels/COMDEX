# backend/tools/build_crystals_from_trace.py
from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.modules.holo.crystal_motifs import extract_motifs_from_glyph_trace
from backend.modules.holo.crystal_holo_packer import build_and_save_crystal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TRACE_PATH = Path("data/qfc/glyph_trace.json")
METRICS_PATH = Path("data/qfc/codex_metrics.json")


def main() -> None:
    if not TRACE_PATH.exists():
        raise SystemExit(f"No glyph_trace found at {TRACE_PATH}")

    trace = json.loads(TRACE_PATH.read_text())
    if not isinstance(trace, list):
        raise SystemExit("glyph_trace.json must be a list of events")

    metrics: dict = {}
    if METRICS_PATH.exists():
        try:
            metrics = json.loads(METRICS_PATH.read_text())
        except Exception as e:
            logger.warning("Failed to load codex_metrics.json: %s", e)

    motifs = extract_motifs_from_glyph_trace(
        glyph_trace=trace,
        codex_metrics=metrics,
        max_length=5,
        min_support=3,
        max_motifs=8,
    )

    if not motifs:
        logger.info("No motifs found in trace.")
        return

    logger.info("Found %d motifs, building crystals…", len(motifs))

    for m in motifs:
        holo = build_and_save_crystal(
            motif=m,
            owner_kind="user",
            owner_id="devtools",
            revision=1,
        )
        uri = holo.get("metadata", {}).get("crystal", {}).get("uri")
        path = holo.get("metadata", {}).get("storage", {}).get("path")
        logger.info("Crystal %s -> %s (%s)", m.motif_id, uri, path)


if __name__ == "__main__":
    main()