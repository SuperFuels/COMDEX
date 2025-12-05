# backend/modules/holo/aion_holo_memory.py

"""
Adapters that turn AION's internal memory + rulebooks into
DevTools-friendly HoloSeed structures.

Used by:
  - /api/holo/aion/seeds/combined
  - /api/holo/aion/seeds/memory
  - /api/holo/aion/seeds/rulebooks
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# --- Repo root + storage locations -------------------------------------------

# This file lives under: backend/modules/holo/aion_holo_memory.py
# repo root = three levels up from here
REPO_ROOT = Path(__file__).resolve().parents[3]

AION_MEMORY_STORE = REPO_ROOT / "data/aion/memory_store.json"
RESONANCE_STATE_STORE = REPO_ROOT / "data/aion/resonance_state.json"
RULEBOOK_INDEX_STORE = REPO_ROOT / "data/rulebooks/rulebook_index.json"

AION_CONTAINER_ID = "aion_memory::core"


# --- Dataclasses -------------------------------------------------------------

@dataclass
class AionMemorySeed:
    seed_id: str
    container_id: str
    kind: str
    label: str
    created_at: str
    tags: List[str]
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AionRulebookSeed:
    seed_id: str
    container_id: str
    rulebook_id: str
    created_at: str
    updated_at: str
    usage_count: int
    tags: List[str]
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --- Helpers -----------------------------------------------------------------

def _ts_to_iso(ts: float | int | None) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        logger.info(f"[AionHoloMemory] JSON store not found: {path}")
        return {}
    try:
        txt = path.read_text()
        data = json.loads(txt)
        if not isinstance(data, dict):
            logger.warning(f"[AionHoloMemory] {path} is not an object at top-level")
            return {}
        logger.info(f"[AionHoloMemory] Loaded {len(data)} entries from {path}")
        return data
    except Exception as e:
        logger.warning(f"[AionHoloMemory] Failed to load {path}: {e}")
        return {}


# --- Memory seeds (resonance-first) -----------------------------------------

def get_aion_memory_holo_seeds(limit: int = 32) -> List[AionMemorySeed]:
    """
    Build memory seeds for DevTools.

    Priority:
      1) data/aion/resonance_state.json   (resonance memories)
      2) data/aion/memory_store.json      (lexicon metrics fallback)
    """
    seeds: List[AionMemorySeed] = []

    # 1) Try resonance_state.json (resonance memories)
    resonance = _load_json(RESONANCE_STATE_STORE)

    if resonance:
        items: List[Tuple[float, str, Dict[str, Any]]] = []
        for term, entry in resonance.items():
            ts = entry.get("timestamp", 0)
            items.append((float(ts or 0.0), term, entry))

        # newest first
        items.sort(key=lambda t: t[0], reverse=True)
        items = items[:limit]

        for ts, term, entry in items:
            ts_iso = _ts_to_iso(ts)
            metrics = {
                "SQI": entry.get("SQI"),
                "rho": entry.get("ρ"),
                "I_bar": entry.get("Ī"),
                "E": entry.get("E"),
            }
            keywords = entry.get("keywords") or []

            payload = {
                "label": term,
                "timestamp": ts_iso,
                "content": ", ".join(keywords) or term,
                "source": "ResonanceState",
                "metrics": {k: v for k, v in metrics.items() if v is not None},
                "keywords": keywords,
            }

            tags = ["resonance"]
            if keywords:
                tags += ["keyword:" + k for k in keywords[:4]]

            seeds.append(
                AionMemorySeed(
                    seed_id=f"res:{term}",
                    container_id=AION_CONTAINER_ID,
                    kind="memory",
                    label=term,
                    created_at=ts_iso,
                    tags=tags,
                    payload=payload,
                )
            )

    # 2) Fallback: memory_store.json if resonance is empty or failed
    if not seeds:
        raw = _load_json(AION_MEMORY_STORE)
        if raw:
            items: List[Tuple[float, str, Dict[str, Any]]] = []
            for lexeme, entry in raw.items():
                ts = entry.get("timestamp", 0)
                items.append((float(ts or 0.0), lexeme, entry))

            items.sort(key=lambda t: t[0], reverse=True)
            items = items[:limit]

            for ts, lexeme, entry in items:
                ts_iso = _ts_to_iso(ts)
                source = entry.get("signed_by", "Tessaris-Core")
                metrics = {
                    "SQI": entry.get("SQI"),
                    "rho": entry.get("ρ"),
                    "I_bar": entry.get("Ī"),
                    "E": entry.get("E"),
                    "sqi_score": entry.get("sqi_score"),
                }

                payload = {
                    "label": lexeme,
                    "timestamp": ts_iso,
                    "content": (
                        f"Lexeme '{lexeme}' with SQI={metrics['SQI']} "
                        f"ρ={metrics['rho']} Ī={metrics['I_bar']} E={metrics['E']}"
                    ),
                    "source": source,
                    "metrics": {k: v for k, v in metrics.items() if v is not None},
                }

                seeds.append(
                    AionMemorySeed(
                        seed_id=f"lex:{lexeme}",
                        container_id=AION_CONTAINER_ID,
                        kind="memory",
                        label=lexeme,
                        created_at=ts_iso,
                        tags=["lexicon", "SQI"],
                        payload=payload,
                    )
                )

    # 3) As a last resort, stub boot memory so UI isn’t totally blank
    if not seeds:
        boot_ts = datetime.now(timezone.utc).isoformat()
        seeds.append(
            AionMemorySeed(
                seed_id="mem:welcome",
                container_id=AION_CONTAINER_ID,
                kind="memory",
                label="AION booted in DevTools",
                created_at=boot_ts,
                tags=["system", "boot"],
                payload={
                    "label": "AION booted",
                    "timestamp": boot_ts,
                    "content": "AION runtime started and is now streaming GHX.",
                    "source": "System",
                },
            )
        )

    return seeds


# --- Rulebook seeds ----------------------------------------------------------

def get_rulebook_holo_seeds() -> List[AionRulebookSeed]:
    """
    Adapt RuleBookIndex → AionRulebookSeed[].

    Reads data/rulebooks/rulebook_index.json directly; if it doesn't exist
    or is empty we just return a stub DevTools rulebook entry.
    """
    seeds: List[AionRulebookSeed] = []

    index_data = _load_json(RULEBOOK_INDEX_STORE)

    # index_data: { rulebook_id: { created_at, updated_at, usage_count, tags, name, description, domains, metrics, ... } }
    for rulebook_id, meta in index_data.items():
        created_ts = _ts_to_iso(meta.get("created_at"))
        updated_ts = _ts_to_iso(meta.get("updated_at"))
        usage = int(meta.get("usage_count", 0))
        tags = meta.get("tags") or ["rulebook"]

        payload = {
            "name": meta.get("name", rulebook_id),
            "description": meta.get("description", ""),
            "domains": meta.get("domains", []),
            "metrics": meta.get("metrics", {}),
        }

        seeds.append(
            AionRulebookSeed(
                seed_id=f"rulebook:{rulebook_id}",
                container_id=AION_CONTAINER_ID,
                rulebook_id=rulebook_id,
                created_at=created_ts,
                updated_at=updated_ts,
                usage_count=usage,
                tags=tags,
                payload=payload,
            )
        )

    # If there are none yet, keep a single stub rulebook so the UI has something
    if not seeds:
        now_iso = datetime.now(timezone.utc).isoformat()
        seeds.append(
            AionRulebookSeed(
                seed_id="rulebook:devtools-basics",
                container_id=AION_CONTAINER_ID,
                rulebook_id="devtools.aion.memory.basics",
                created_at=now_iso,
                updated_at=now_iso,
                usage_count=1,
                tags=["rulebook", "devtools"],
                payload={
                    "name": "DevTools AION Memory Basics",
                    "description": (
                        "Internal rules for how AION snapshots and visualises "
                        "its memory field in DevTools."
                    ),
                    "domains": ["devtools", "memory", "visualisation"],
                    "metrics": {
                        "Φ_coherence": 0.9,
                        "Φ_entropy": 0.3,
                        "SQI": 0.82,
                    },
                },
            )
        )

    seeds.sort(key=lambda s: s.usage_count, reverse=True)
    return seeds


# --- Combined view -----------------------------------------------------------

def get_combined_holo_seeds(limit_memory: int = 32) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convenience helper used by /api/holo/aion/seeds/combined.
    """
    memory_seeds = get_aion_memory_holo_seeds(limit=limit_memory)
    rulebook_seeds = get_rulebook_holo_seeds()

    return {
        "memory": [s.to_dict() for s in memory_seeds],
        "rulebooks": [s.to_dict() for s in rulebook_seeds],
    }