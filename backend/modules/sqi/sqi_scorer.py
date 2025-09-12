from typing import Dict, List, Any
import time

# Optional: hook into live metrics bus if present
try:
    from backend.modules.sqi.metrics_bus import metrics_bus
except ImportError:
    metrics_bus = None


def score_electron_glyph(glyph: Dict[str, Any]) -> float:
    """
    Compute an SQI score for a single electron glyph based on logic_trace or prediction.

    Criteria:
    - Confidence (higher is better)
    - Entropy (lower is better)
    - Status: simplify > valid > unknown > contradiction

    Returns:
        float score in [0, 1]
    """
    trace = glyph.get("logic_trace", [])
    prediction = glyph.get("prediction", {})

    if trace and isinstance(trace, list):
        latest = trace[-1]
    else:
        latest = prediction

    confidence = float(latest.get("confidence", 0.5))
    entropy = float(latest.get("entropy", 1.0))
    status = latest.get("status", "unknown")

    # Normalize
    confidence_score = max(0.0, min(confidence, 1.0))
    entropy_score = 1.0 - max(0.0, min(entropy, 1.0))

    status_bonus = {
        "simplify": 0.2,
        "valid": 0.1,
        "unknown": -0.1,
        "contradiction": -0.2,
    }.get(status, 0.0)

    total_score = confidence_score * 0.6 + entropy_score * 0.4 + status_bonus
    return max(0.0, min(total_score, 1.0))


def score_all_electrons(data: Any) -> Dict[str, Dict[str, Any]]:
    """
    Accepts either:
    - A Codex container dict with "glyphs" (legacy mode), OR
    - A list of WaveState or glyph dicts (EntangledWave mode)

    Returns:
        Dict mapping glyph id → score payload
    """
    from backend.modules.sqi.metrics_bus import metrics_bus

    results = {}

    if isinstance(data, dict) and "glyphs" in data:
        glyphs = data["glyphs"]
    elif isinstance(data, list):
        glyphs = data
    else:
        return {}

    for glyph in glyphs:
        if isinstance(glyph, dict):
            gid = glyph.get("id") or glyph.get("uid")
            label = glyph.get("label", "")
            score = score_electron_glyph(glyph)
            status = "unknown"
            trace = glyph.get("logic_trace", [])
            if trace and isinstance(trace, list):
                status = trace[-1].get("status", "unknown")
            elif "prediction" in glyph:
                status = glyph["prediction"].get("status", "unknown")
        else:
            # Assume it's a WaveState object
            gid = getattr(glyph, "id", None)
            label = getattr(glyph, "label", "")
            metadata = getattr(glyph, "metadata", {})
            score = score_electron_glyph(metadata)
            status = metadata.get("prediction", {}).get("status", "unknown")

        results[gid] = {
            "id": gid,
            "score": score,
            "label": label,
            "status": status,
        }

        if metrics_bus and gid:
            old_score = glyph.get("sqi_score", None) if isinstance(glyph, dict) else None
            if old_score is not None:
                delta = score - old_score
                metrics_bus.push({
                    "event_type": "coherence_shift",
                    "node_id": gid,
                    "label": label,
                    "delta": delta,
                    "old_score": old_score,
                    "new_score": score,
                    "status": status,
                    "timestamp": time.time(),
                })

    return results

def score_pattern_sqi(pattern: Dict[str, Any]) -> float:
    """
    Compute an SQI score for a symbolic pattern based on:
    - Uniqueness (entropy)
    - Symmetry (repetition)
    - Length normalization
    - Optional: trigger logic, alignment, emotion, etc.

    Returns:
        float score in [0.0, 1.0]
    """
    glyphs = pattern.get("glyphs", [])
    if not glyphs:
        return 0.0

    total = len(glyphs)
    from backend.modules.patterns.pattern_registry import stringify_glyph
    unique = len(set(stringify_glyph(g) for g in glyphs))
    symmetry = total - unique  # higher means more repetition
    entropy_ratio = unique / total if total else 0.0

    # Weight config
    w_entropy = 0.6
    w_symmetry = 0.3
    w_length_bonus = 0.1

    # Score composition
    score = (
        (1.0 - entropy_ratio) * w_entropy +
        (symmetry / total) * w_symmetry +
        min(0.1, total / 20.0) * w_length_bonus
    )

    return round(min(max(score, 0.0), 1.0), 4)

def compute_entropy(glyphs: List[str]) -> float:
    if not glyphs:
        return 1.0
    unique = set(glyphs)
    return 1.0 - (len(unique) / len(glyphs))


def compute_symmetry_score(glyphs: List[str]) -> float:
    if not glyphs:
        return 0.0
    reversed_glyphs = glyphs[::-1]
    matches = sum(1 for a, b in zip(glyphs, reversed_glyphs) if a == b)
    return matches / len(glyphs)

def inject_sqi_scores_into_container(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes and injects SQI scores for all electron glyphs into the container.
    Adds `sqi_score` to each relevant glyph in-place.

    Returns:
        Updated container dict.
    """
    scored = score_all_electrons(container)
    score_map = {s["id"]: s["score"] for s in scored}

    for glyph in container.get("glyphs", []):
        gid = glyph.get("id")
        if gid in score_map:
            glyph["sqi_score"] = score_map[gid]

    return container