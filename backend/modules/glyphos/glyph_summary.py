# glyph_summary.py

from collections import defaultdict
import hashlib

# Categorize glyphs based on symbolic type
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
    "🧬": "mutation"
}

_last_hash = None  # For change detection


def summarize_glyphs(cubes: dict) -> dict:
    total = 0
    by_type = defaultdict(int)
    by_category = defaultdict(int)
    lifespan_sum = 0
    lifespan_count = 0
    decaying = 0
    expired = 0

    coords = sorted(cubes.keys())
    glyph_signature = ""

    for coord in coords:
        cube = cubes.get(coord, {})
        glyph = cube.get("glyph", "").strip()

        if not glyph:
            continue

        total += 1
        by_type[glyph] += 1

        # Determine category
        category = GLYPH_CATEGORIES.get(glyph, "unknown")
        by_category[category] += 1

        # Track lifespan
        if "lifespan" in cube:
            lifespan_sum += cube["lifespan"]
            lifespan_count += 1
            if cube.get("decay", False):
                decaying += 1
                if cube["lifespan"] <= 0:
                    expired += 1

        # Signature for change detection
        glyph_signature += f"{coord}:{glyph}:{cube.get('lifespan','')};"

    # Change detection
    global _last_hash
    current_hash = hashlib.md5(glyph_signature.encode()).hexdigest()
    changed = _last_hash != current_hash
    _last_hash = current_hash

    return {
        "total": total,
        "by_type": dict(by_type),
        "by_category": dict(by_category),
        "decaying": decaying,
        "expired": expired,
        "avg_lifespan": round(lifespan_sum / lifespan_count, 2) if lifespan_count > 0 else None,
        "changed_since_last": changed
    }