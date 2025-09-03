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


def score_all_electrons(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Scan all glyphs in a container, find those of type 'electron',
    and score them using SQI logic.

    Returns:
        List of dicts with {id, score, label, status}
    """
    glyphs = container.get("glyphs", [])
    results = []

    for glyph in glyphs:
        if glyph.get("type") != "electron":
            continue

        old_score = glyph.get("sqi_score", None)
        new_score = score_electron_glyph(glyph)

        status = None
        trace = glyph.get("logic_trace", [])
        if trace and isinstance(trace, list):
            status = trace[-1].get("status")
        if not status:
            status = glyph.get("prediction", {}).get("status", "unknown")

        results.append({
            "id": glyph.get("id"),
            "score": new_score,
            "label": glyph.get("label", ""),
            "status": status,
        })

        # Optional: Track coherence gain/loss
        if old_score is not None and metrics_bus:
            delta = new_score - old_score
            metrics_bus.push({
                "event_type": "coherence_shift",
                "node_id": glyph.get("id"),
                "label": glyph.get("label", ""),
                "delta": delta,
                "old_score": old_score,
                "new_score": new_score,
                "status": status,
                "timestamp": time.time(),
            })

    return sorted(results, key=lambda x: -x["score"])


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