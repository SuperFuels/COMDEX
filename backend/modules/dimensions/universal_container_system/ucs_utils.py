# File: backend/modules/dimensions/universal_container_system/ucs_utils.py

"""
🔧 UCS Utils - Universal Container Helpers
------------------------------------------
Provides utility functions for normalizing, validating, or describing UCS container inputs.

Used in:
- UCSRuntime
- Container Loader
- GHX Visualizer
- Symbol Tree Generator
"""

import hashlib
import re
from typing import Any, Dict, Optional, Tuple


# -------------------------------
# 🔄 Container Normalization
# -------------------------------

def normalize_container_dict(container_input: Any) -> Dict[str, Any]:
    """
    Normalize any container input (dict or UCSBaseContainer subclass) to a plain dict.

    Accepts:
    - Raw dict
    - UCSBaseContainer or compatible .to_dict() object

    Returns:
    - Normalized dict representation for UCS runtime

    Raises:
    - TypeError if input is not supported
    """
    if isinstance(container_input, dict):
        return container_input

    # Dynamically import to avoid circular dependencies
    from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

    if isinstance(container_input, UCSBaseContainer):
        return container_input.to_dict()

    # Support fallback to_dict method (for symbolic containers or expansion types)
    if hasattr(container_input, "to_dict"):
        return container_input.to_dict()

    raise TypeError(f"Unsupported container input: {type(container_input)}")


# -------------------------------
# 🌐 UCS Geometries + Symbols
# -------------------------------

UCS_GEOMETRY_SYMBOLS = {
    "Tetrahedron": "🔻",
    "Octahedron": "🟣",
    "Icosahedron": "🔶",
    "Dodecahedron": "🔷",
    "Tesseract": "🧮",
    "Quantum Orb": "⚛️",
    "Vortex": "🌪️",
    "Black Hole": "🪐",
    "Torus": "🧿",
    "DNA Spiral": "🧬",
    "Fractal Crystal": "🧊",
    "Memory Pearl": "🧿",
    "Mirror Container": "🪞",
    "Field Resonance Chamber": "🎛️",
    "Compression Core": "🌀",
    "Plasma Exciter": "🔥",
    "Vortex Chamber": "🌪️",
    "Torus Recycler": "♾️",
    "Wave Exhaust Nozzle": "💨",
}

def compute_ucs_hash(identifier: str) -> str:
    """Generate a UCS-safe hash for container identity."""
    return hashlib.sha256(identifier.encode()).hexdigest()[:12]

def normalize_geometry_name(name: str) -> str:
    """Sanitize and title-case geometry names."""
    return re.sub(r"[^a-zA-Z0-9 ]", "", name).strip().title()

def get_geometry_symbol(geometry_type: str) -> str:
    """Get associated unicode symbol for a UCS geometry."""
    return UCS_GEOMETRY_SYMBOLS.get(geometry_type, "📦")

def describe_geometry_type(geometry_type: str) -> str:
    """Return description or symbolic role of the geometry."""
    return {
        "Tesseract": "Entangled futures container",
        "Quantum Orb": "Probabilistic glyph states",
        "DNA Spiral": "Mutation lineage growth",
        "Mirror Container": "Self-reference and reflection triggers",
        "Field Resonance Chamber": "SQI resonance field harmonization",
        "Compression Core": "Extreme density collapse stage",
        "Black Hole": "Entropy sink and compression",
    }.get(geometry_type, "Generic symbolic container")

def validate_geometry(geometry_type: str) -> bool:
    """Ensure geometry is one of the known UCS types."""
    return geometry_type in UCS_GEOMETRY_SYMBOLS


# -------------------------------
# 🛰️ UCS URIs + Linking
# -------------------------------

def generate_ucs_uri(container_id: str, label: str = "container") -> str:
    """Generate a UCS-compatible URI for container linking."""
    return f"ucs://local/{container_id}#{label}"

def parse_ucs_uri(uri: str) -> Tuple[str, str]:
    """Extract container ID and label from UCS URI."""
    match = re.match(r"ucs://local/([^#]+)#(.+)", uri)
    if match:
        return match.group(1), match.group(2)
    return "unknown", "unknown"

def resolve_wormhole_path(source: str, destination: str) -> str:
    """
    Construct a symbolic wormhole path from one container to another.

    Example:
        source: 'container_alpha'
        destination: 'container_beta'
        -> 'wormhole://container_alpha->container_beta'
    """
    return f"wormhole://{source}->{destination}"

# -------------------------------
# 🧠 Microgrid + Time Helpers
# -------------------------------

def get_microgrid_dimensions(size: str = "default") -> Tuple[int, int, int]:
    """Return default microgrid size for symbolic voxel layout."""
    if size == "large":
        return (8, 8, 8)
    elif size == "mini":
        return (2, 2, 2)
    return (4, 4, 4)

def apply_time_dilation_factor(speed: float) -> float:
    """Apply time dilation for symbolic runtime containers."""
    if speed <= 0:
        return 1.0
    return round(1.0 / speed, 3)