# backend/modules/holo/crystal_container.py

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.modules.dna_chain.dna_switch import DNA_SWITCH

DNA_SWITCH.register(__file__)
logger = logging.getLogger(__name__)

CRYSTAL_ROOT = Path("data/crystals").expanduser()


@dataclass
class CrystalContainer:
    """
    Simple file-based container for 'crystal' holos (compressed motifs).

    Scope is a logical path like 'user/devtools'.
    Files live under: data/crystals/<scope>/*.holo.json
    """

    scope: str = "user/devtools"

    @property
    def root(self) -> Path:
        return CRYSTAL_ROOT / self.scope

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def list_holo_paths(self) -> List[Path]:
        self.ensure_dirs()
        return sorted(self.root.glob("*.holo.json"))

    def next_tick(self) -> int:
        files = self.list_holo_paths()
        if not files:
            return 0
        last = files[-1].name  # e.g. motif-0007__t=7_v1.holo.json
        try:
            stem = Path(last).stem               # motif-0007__t=7_v1
            tick_part = stem.split("__", 1)[1]   # t=7_v1
            tick_str = tick_part.split("_", 1)[0].split("=", 1)[1]  # "7"
            return int(tick_str) + 1
        except Exception:
            return 0


def save_crystal_holo(container: CrystalContainer, holo: Dict[str, Any]) -> Path:
    """
    Persist a crystal holo into its scope folder.

    Filename: motif-XXXX__t=T_vR.holo.json
    """
    container.ensure_dirs()

    motif_id = (
        holo.get("metadata", {})
        .get("motif", {})
        .get("motif_id")
        or "motif"
    )
    # strip "motif:" prefix if present
    motif_suffix = motif_id.split(":", 1)[-1]

    tick = int(holo.get("tick", 0))
    revision = int(holo.get("revision", 1))

    filename = f"motif-{motif_suffix}__t={tick}_v{revision}.holo.json"
    path = container.root / filename

    with path.open("w") as f:
        json.dump(holo, f, indent=2)

    logger.info("[CrystalContainer] Saved crystal holo -> %s", path)
    return path


def load_crystal_holo(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("[CrystalContainer] Failed to load %s: %s", path, e)
        return None