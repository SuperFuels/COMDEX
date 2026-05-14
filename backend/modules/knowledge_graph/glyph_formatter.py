import hashlib
import time
from typing import Dict, Any, List, Optional

# 🔧 Optional: For entanglement/trace hooks if available
try:
    from backend.modules.glyphos.glyph_trace_logger import glyph_trace
except ImportError:
    glyph_trace = None

# ✅ GHX Prediction Formatter
def format_prediction_for_ghx(prediction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a predictive glyph path into a GHX-compatible payload for rendering in the GHXVisualizer.
    
    Args:
        prediction: Dict containing glyph prediction details.
    
    Returns:
        Dict structured for GHX rendering.
    """
    glyph = prediction.get("glyph", "∅")
    coord = prediction.get("coord", "0,0,0")
    confidence = float(prediction.get("confidence", 1.0))
    fork_id = prediction.get("id") or generate_fork_id(glyph, coord)
    emotion = prediction.get("emotion", "neutral")
    container_id = prediction.get("container_id", "unknown")
    entangled_with = prediction.get("entangled_with", None)

    return {
        "id": fork_id,
        "glyph": glyph,
        "coord": coord,
        "confidence": confidence,
        "emotion": emotion,
        "container_id": container_id,
        "timestamp": time.time(),
        "entangled_with": entangled_with,
        "visual": build_ghx_visual_metadata(glyph, confidence, emotion, entangled_with),
    }

# ✅ Generate deterministic fork ID
def generate_fork_id(glyph: str, coord: str) -> str:
    seed = f"{glyph}:{coord}:{time.time()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]

# ✅ Build GHX visual metadata (geometry, color, pulse)
def build_ghx_visual_metadata(glyph: str, confidence: float, emotion: str, entangled_with: Optional[str]) -> Dict[str, Any]:
    """
    Construct visualization attributes for GHX rendering.
    """
    return {
        "geometry": map_glyph_to_geometry(glyph),
        "color": map_emotion_to_color(emotion, confidence),
        "pulse": confidence_to_pulse(confidence),
        "entangled": bool(entangled_with),
    }

# 🔗 Glyph -> Geometry mapping for GHX
def map_glyph_to_geometry(glyph: str) -> str:
    if "↔" in glyph: return "Tesseract 🧮"
    if "🧬" in glyph: return "DNA Spiral 🧬"
    if "⚛" in glyph: return "Quantum Orb ⚛️"
    if "🌪" in glyph: return "Vortex 🌪️"
    if "🪞" in glyph: return "Mirror Container 🪞"
    if "🪐" in glyph: return "Black Hole 🪐"
    return "Tetrahedron 🔻"

# 🔮 Emotion -> Color mapping
def map_emotion_to_color(emotion: str, confidence: float) -> str:
    base_colors = {
        "joy": "#FFD700",       # Gold
        "neutral": "#9CA3AF",   # Gray
        "focus": "#2563EB",     # Blue
        "fear": "#DC2626",      # Red
        "curiosity": "#10B981", # Green
    }
    color = base_colors.get(emotion, "#9CA3AF")
    # Fade color if confidence is low
    return fade_color(color, confidence)

def fade_color(hex_color: str, factor: float) -> str:
    """Adjust brightness of hex color based on confidence factor (0-1)."""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    adjusted = tuple(int(c * max(0.2, factor)) for c in rgb)
    return '#%02x%02x%02x' % adjusted

# 🔁 Confidence pulse scaling
def confidence_to_pulse(confidence: float) -> float:
    return max(0.2, min(1.0, confidence))

# ✅ Batch formatter for multiple predictions
def batch_format_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [format_prediction_for_ghx(p) for p in predictions]

# 🧪 Diagnostic Entry Point
if __name__ == "__main__":
    sample_prediction = {
        "glyph": "↔(🧬)",
        "coord": "3,2,1",
        "confidence": 0.72,
        "emotion": "curiosity",
        "container_id": "demo_container",
        "entangled_with": "seed_123",
    }
    print("GHX Payload:", format_prediction_for_ghx(sample_prediction))