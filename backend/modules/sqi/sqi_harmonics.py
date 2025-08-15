# -*- coding: utf-8 -*-
# backend/modules/sqi/sqi_harmonics.py

from __future__ import annotations
from typing import Any, Dict, List, Tuple, Iterable, Union
import json
import os
import re

ContainerLike = Dict[str, Any]

__all__ = ["suggest_harmonics"]

# ---------- helpers ----------

def _load_container(path: str) -> ContainerLike:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _logic_entries(container: ContainerLike) -> List[Dict[str, Any]]:
    for f in (
        "symbolic_logic",
        "expanded_logic",
        "hoberman_logic",
        "exotic_logic",
        "symmetric_logic",
        "axioms",
    ):
        v = container.get(f)
        if isinstance(v, list):
            return v
    return []

_token_re = re.compile(r"[A-Za-z0-9_]+")

def _tokens(s: str) -> List[str]:
    return [t.lower() for t in _token_re.findall(s or "")]

def _score(name: str, logic_texts: Iterable[str], missing: str) -> float:
    """Lightweight similarity score:
       - substring match bonus
       - token overlap across name + logic fragments
    """
    m = (missing or "").lower().strip()
    if not m:
        return 0.0

    score = 0.0

    # 1) direct substring in name
    nm = (name or "").lower()
    if m in nm:
        score += 1.0

    # 2) token overlap (Jaccard-ish) on name + logic texts
    cand_tokens = set(_tokens(nm))
    for txt in logic_texts:
        cand_tokens.update(_tokens(txt))

    miss_tokens = set(_tokens(m))
    if cand_tokens and miss_tokens:
        inter = len(cand_tokens & miss_tokens)
        union = len(cand_tokens | miss_tokens)
        score += 2.0 * (inter / union)  # weighted a bit higher than substring

    return round(score, 4)

# ---------- public API ----------

def suggest_harmonics(
    container_or_path: Union[ContainerLike, str],
    missing: str,
    top_k: int = 3,
) -> List[Tuple[str, float]]:
    """
    Return up to top_k candidate entries from the same container that are likely
    to satisfy the missing dependency name.

    Shape matches what your route expects:
        List[Tuple[name, score]]
    """
    container: ContainerLike = (
        _load_container(container_or_path) if isinstance(container_or_path, str) else container_or_path
    )

    entries = _logic_entries(container)
    # Build candidate list (exclude items with no name)
    scored: List[Tuple[str, float]] = []
    for e in entries:
        name = e.get("name")
        if not name:
            continue
        # collect any textual context we can use
        texts = []
        if isinstance(e.get("logic"), str):
            texts.append(e["logic"])
        if isinstance(e.get("logic_raw"), str):
            texts.append(e["logic_raw"])
        cl = e.get("codexlang") or {}
        if isinstance(cl.get("logic"), str):
            texts.append(cl["logic"])

        s = _score(name, texts, missing)
        if s > 0.0:
            scored.append((name, s))

    scored.sort(key=lambda t: t[1], reverse=True)
    if top_k and top_k > 0:
        scored = scored[:top_k]
    return scored