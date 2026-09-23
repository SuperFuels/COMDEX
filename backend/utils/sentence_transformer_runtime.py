"""Process-wide, resource-bounded SentenceTransformer loader.

The legacy backend imports several subsystems that each historically created an
independent MiniLM instance.  On Apple Silicon the automatic device selection
placed every copy on MPS; a Tessaris startup could consequently allocate nearly
all unified memory before the HTTP server became ready.

All callers now share one model per canonical path/device/options tuple.  The
desktop process sets ``AION_EMBEDDING_DEVICE=cpu`` so embeddings cannot exhaust
MPS memory; other runtimes may explicitly select another device.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any


_MODEL_CACHE: dict[tuple[str, str, tuple[tuple[str, str], ...]], Any] = {}
_MODEL_CACHE_LOCK = threading.RLock()


def _canonical_model_name(model_name_or_path: str | Path) -> str:
    raw = str(model_name_or_path)
    path = Path(raw).expanduser()
    if path.exists():
        return str(path.resolve())
    return raw


def get_sentence_transformer(model_name_or_path: str | Path, **kwargs: Any) -> Any:
    """Return a cached SentenceTransformer using the governed device policy."""

    from sentence_transformers import SentenceTransformer

    model_name = _canonical_model_name(model_name_or_path)
    device = str(
        kwargs.pop("device", None)
        or os.getenv("AION_EMBEDDING_DEVICE", "")
    ).strip()
    if device:
        kwargs["device"] = device

    option_key = tuple(sorted((str(key), repr(value)) for key, value in kwargs.items()))
    cache_key = (model_name, device or "automatic", option_key)

    with _MODEL_CACHE_LOCK:
        model = _MODEL_CACHE.get(cache_key)
        if model is None:
            model = SentenceTransformer(model_name, **kwargs)
            _MODEL_CACHE[cache_key] = model
        return model


def sentence_transformer_cache_size() -> int:
    """Expose a small diagnostic without leaking model objects."""

    with _MODEL_CACHE_LOCK:
        return len(_MODEL_CACHE)
