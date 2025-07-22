from collections import defaultdict
import hashlib

GLYPH_CATEGORIES = {
    "✦": "memory",
    "🧠": "logic",
    "⚛": "emotion",
    "🔁": "loop",
    "🧽": "decay",
    "💡": "insight",
    "⛓": "link",
    "🎯": "goal",
    "📜": "scroll",
    "🧬": "mutation",
    "↔": "logic",
    "⊕": "logic",
    "⟲": "loop",
    "→": "logic",
    "⧖": "logic",
}

GLYPH_WEIGHTS = {
    "⚛": 2.0,
    "🧠": 1.2,
    "🧬": 1.5,
    "↔": 0.8,
    "⊕": 0.6,
    "⟲": 0.7,
    "→": 0.5,
    "⧖": 0.6,
}

_last_hash = None
_last_coords = set()

def summarize_glyphs(cubes: dict, state_manager=None) -> dict:
    total = 0
    by_type = defaultdict(int)
    by_category = defaultdict(int)
    lifespan_sum = 0
    lifespan_count = 0
    decaying = 0
    expired = 0
    oldest = 0
    youngest = None
    emotion_score = 0
    glyph_signature = ""
    seen_glyphs = set()
    current_coords = set()

    for coord, cube in cubes.items():
        glyph = cube.get("glyph", "").strip()
        if not glyph:
            continue

        total += 1
        by_type[glyph] += 1
        seen_glyphs.add(glyph)
        current_coords.add(coord)

        # Category logic
        category = GLYPH_CATEGORIES.get(glyph, "unknown")
        by_category[category] += 1

        # Emotional / cognitive scoring
        emotion_score += GLYPH_WEIGHTS.get(glyph, 0)

        # Lifespan logic
        if "lifespan" in cube:
            lifespan = cube["lifespan"]
            lifespan_sum += lifespan
            lifespan_count += 1

            if lifespan > oldest:
                oldest = lifespan
            if youngest is None or lifespan < youngest:
                youngest = lifespan

            if cube.get("decay", False):
                decaying += 1
                if lifespan <= 0:
                    expired += 1

        glyph_signature += f"{coord}:{glyph}:{cube.get('lifespan','')};"

    # Change detection
    global _last_hash, _last_coords
    current_hash = hashlib.md5(glyph_signature.encode()).hexdigest()
    changed = current_hash != _last_hash
    changed_coords = sorted(current_coords - _last_coords) if changed else []

    _last_hash = current_hash
    _last_coords = current_coords

    # Volume estimation (for density)
    volume = max(len(cubes), 1)
    density = round(total / volume, 4)

    dominant_category = max(by_category.items(), key=lambda x: x[1], default=(None, 0))[0]

    summary = {
        "total": total,
        "types": dict(by_type),
        "by_category": dict(by_category),
        "active_symbols": sorted(list(seen_glyphs)),
        "dominant_category": dominant_category,
        "changed": changed,
        "recent_changes": changed_coords,
        "decayed": decaying,
        "expired": expired,
        "emotion_score": round(emotion_score, 2),
        "density": density,
        "lifespanStats": {
            "average": round(lifespan_sum / lifespan_count, 2) if lifespan_count > 0 else 0,
            "oldest": oldest,
            "youngest": youngest if youngest is not None else 0
        }
    }

    if state_manager and hasattr(state_manager, "get_tick"):
        try:
            summary["tick"] = state_manager.get_tick()
        except Exception:
            pass

    return summary