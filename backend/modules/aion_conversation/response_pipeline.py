from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.aion_conversation.minimal_response_composer import (
    MinimalResponseComposer,
    AionKnowledgeState,
)
from backend.modules.aion_learning.teaching_applier import apply_teaching_to_ks
from backend.modules.aion_learning.teaching_memory_store import TeachingMemoryStore
from backend.modules.aion_learning.teaching_retriever import TeachingRetriever


TEACHING_MEMORY_FILE = Path("data/logs/phase0_learning_memory.json")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _to_plain_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    return {"value": obj}


def compose_aion_response(
    *,
    user_text: str,
    ks: AionKnowledgeState,
    enable_teaching: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Phase 0.2 runtime response pipeline:
    - optional teaching application (feature-flagged)
    - minimal response composition
    - standardized return payload
    """
    ks_local = deepcopy(ks)
    composer = MinimalResponseComposer()

    if enable_teaching is None:
        enable_teaching = _env_flag("AION_ENABLE_TEACHING_APPLY", default=False)

    teaching_meta: Dict[str, Any] = {
        "teaching_applied": False,
        "applied_concepts": [],
        "teaching_match_score": 0.0,
        "teaching_match_reasons": [],
    }

    if enable_teaching:
        store = TeachingMemoryStore(TEACHING_MEMORY_FILE)
        retriever = TeachingRetriever(min_score=1.0)

        # Feature-flagged and non-fatal
        try:
            teaching_meta = apply_teaching_to_ks(
                ks=ks_local,
                user_text=user_text,
                store=store,
                retriever=retriever,
            )
        except Exception as e:
            teaching_meta = {
                "teaching_applied": False,
                "applied_concepts": [],
                "teaching_match_score": 0.0,
                "teaching_match_reasons": [f"teaching_apply_error:{type(e).__name__}"],
            }

    composed = composer.compose(user_text=user_text, ks=ks_local)

    metadata = _to_plain_dict(getattr(composed, "metadata", {}))
    metadata.update(teaching_meta)
    metadata["phase"] = "phase0_2_runtime_pipeline"

    return {
        "text": str(getattr(composed, "text", "")),
        "confidence": float(getattr(composed, "confidence", 0.0) or 0.0),
        "metadata": metadata,
        "knowledge_state": {
            "intent": getattr(ks_local, "intent", None),
            "topic": getattr(ks_local, "topic", None),
            "confidence": float(getattr(ks_local, "confidence", 0.0) or 0.0),
            "known_facts": list(getattr(ks_local, "known_facts", []) or []),
            "goals": list(getattr(ks_local, "goals", []) or []),
            "unresolved": list(getattr(ks_local, "unresolved", []) or []),
            "source_refs": list(getattr(ks_local, "source_refs", []) or []),
        },
    }