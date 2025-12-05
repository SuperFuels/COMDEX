# backend/modules/holo/aion_memory_container.py
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.dna_chain.dna_switch import DNA_SWITCH

DNA_SWITCH.register(__file__)
logger = logging.getLogger(__name__)

# Base directory where .holo snapshots live
HOLO_ROOT = Path(os.environ.get("HOLO_ROOT", "data/holo")).expanduser()

# Single canonical container id for AION's memory field
AION_MEMORY_CONTAINER_ID = "aion_memory::core"


@dataclass
class AionMemoryContainer:
    """
    Lightweight container description for the AION memory field.

    This doesn’t try to model the full KG container runtime – it just
    standardises where .holo snapshots for AION’s memory live on disk.
    """

    container_id: str = AION_MEMORY_CONTAINER_ID
    title: str = "AION Memory Field"
    description: str = (
        "Time-folded holograms of AION's internal memory field "
        "(lexicon + resonance + rulebook seeds)."
    )
    # Folder:  data/holo/aion_memory::core/
    root: Path = HOLO_ROOT / AION_MEMORY_CONTAINER_ID

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def list_holo_files(self) -> List[Path]:
        if not self.root.exists():
            return []
        # simple lexicographic sort is fine because filenames embed tick + revision
        return sorted(self.root.glob("*.holo.json"))

    def latest_holo_path(self) -> Optional[Path]:
        files = self.list_holo_files()
        return files[-1] if files else None


def get_aion_memory_container() -> AionMemoryContainer:
    """
    Return the singleton AionMemoryContainer and ensure its folder exists.
    """
    c = AionMemoryContainer()
    c.ensure_dirs()
    return c


def save_aion_memory_holo(holo: Dict[str, Any]) -> Path:
    """
    Persist a .holo snapshot for the AION memory field under the container root.

    File name:  t=<tick>_v<revision>.holo.json
    """
    c = get_aion_memory_container()
    tick = int(holo.get("tick", 0))
    rev = int(holo.get("revision", 1))

    filename = f"t={tick}_v{rev}.holo.json"
    path = c.root / filename

    with open(path, "w") as f:
        json.dump(holo, f, indent=2)

    logger.info("[AionMemoryContainer] Saved holo snapshot -> %s", path)
    return path


def load_latest_aion_memory_holo() -> Optional[Dict[str, Any]]:
    """
    Load the most recent .holo snapshot for the AION memory container, if any.
    """
    c = get_aion_memory_container()
    path = c.latest_holo_path()
    if not path:
        return None

    with open(path, "r") as f:
        holo = json.load(f)

    logger.info("[AionMemoryContainer] Loaded latest holo snapshot <- %s", path)
    return holo