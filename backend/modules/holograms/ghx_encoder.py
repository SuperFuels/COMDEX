import time
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter

from backend.modules.codex.codex_metrics import calculate_glyph_cost
from backend.modules.codex.codex_trace import trace_glyph_execution_path
from backend.modules.codex.symbolic_key_deriver import derive_entropy_hash
from backend.modules.hexcore.memory_engine import get_recent_memory_glyphs

GHX_VERSION = "1.2"

def encode_glyphs_to_ghx(container: Dict[str, Any], qglyph_string: str = "", observer_id: str = "anon") -> Dict[str, Any]:
    # --- HOV3: respect collapsed flag for lazy export ---
    ghx_meta_flags = (container.get("meta") or {}).get("ghx") or {}
    if bool(ghx_meta_flags.get("collapsed", True)):
        return {
            "ghx_version": GHX_VERSION,
            "container_id": container.get("container_id") or container.get("id", "unknown"),
            "generated": datetime.utcnow().isoformat(),
            "physics": container.get("physics", "symbolic-quantum"),
            "dimensions": 4,
            "holographic": True,
            "collapsed": True,
            "replay_enabled": False,
            "reversal_ready": False,
            "holograms": [],  # defer heavy payload
        }

    # --- HOV4: time-dilation sampling (only affects non-collapsed export) ---
    td = (container.get("meta") or {}).get("time_dilation") or {}
    td_mode = td.get("mode", "normal")
    try:
        td_rate = float(td.get("snapshot_rate", 1.0))
    except Exception:
        td_rate = 1.0

    # 🔄 Lazy imports to avoid circular dependency
    from backend.modules.glyphos.symbolic_entangler import get_entangled_links
    from backend.modules.glyphos.glyph_quantum_core import generate_qglyph_from_string

    container_id = container.get("container_id") or container.get("id", "unknown")
    glyphs = container.get("glyphs", [])

    # Apply time-dilation downsampling
    if td_mode == "compressed" and 0.0 < td_rate < 1.0 and glyphs:
        step = max(1, int(round(1.0 / td_rate)))
        glyphs = glyphs[::step]
    elif td_mode == "frozen":
        glyphs = []  # fully suppressed

    # ======== everything below here is your existing logic ========

    entropy_seed = "🧬" + qglyph_string if qglyph_string else None
    entropy_hash = derive_entropy_hash(entropy_seed) if entropy_seed else None
    observer_hash = hashlib.sha256(observer_id.encode()).hexdigest()[:12] if observer_id else None

    # ✅ Load recent memory echoes
    memory_echo_ids = {g["id"] for g in get_recent_memory_glyphs(limit=8)} if hasattr(get_recent_memory_glyphs, "__call__") else set()

    holograms = []
    operator_sequence = []
    for glyph in glyphs:
        glyph_id = glyph.get("id")
        symbol = glyph.get("glyph")
        label = glyph.get("label", "")
        timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())

        entangled = glyph.get("entangled", []) or get_entangled_links(glyph_id)
        light_logic = generate_light_logic(symbol)
        position = generate_spatial_coordinates(glyph_id)
        cost = calculate_glyph_cost({"glyph": symbol})  # ✅ Updated call to pass glyph wrapped dict
        replay = trace_glyph_execution_path(glyph_id)
        narration = generate_narration(symbol, label)

        operator_sequence.append(symbol)
        is_memory_echo = glyph_id in memory_echo_ids

        state_snapshot = {
            "symbol": symbol,
            "label": label,
            "position": position,
            "timestamp": timestamp,
            "entangled": entangled,
            "qentropy_state": entropy_hash,
            "reconstruct_logic": light_logic,
            "memory_echo": is_memory_echo
        }

        holograms.append({
            "id": glyph_id,
            "symbol": symbol,
            "label": label,
            "timestamp": timestamp,
            "entangled": entangled,
            "light_logic": light_logic,
            "position": position,
            "cost": cost,
            "replay": replay,
            "narration": narration,
            "state_snapshot": state_snapshot,
            "memory_echo": is_memory_echo,
            "tts_ready": True,
            "access_control": {
                "entropy_gate": entropy_hash if entropy_hash else None,
                "allowed_observers": [observer_hash] if observer_hash else []
            }
        })

    # ✅ Optional avatar projection glyph
    avatar_projection = {
        "id": f"avatar-{observer_hash}",
        "symbol": "👁️" if entropy_hash else "🧍",
        "label": "Avatar Presence",
        "timestamp": datetime.utcnow().isoformat(),
        "position": {"x": -1.0, "y": -1.0, "z": 0.0},
        "entangled": [],
        "light_logic": {
            "color": "#ddddff",
            "intensity": 0.75,
            "animation": "hover",
            "avatar": True
        },
        "narration": {
            "text_to_speak": f"Observer {observer_id} present",
            "voice": "neutral",
            "language": "en-US"
        },
        "state_snapshot": {
            "observer_hash": observer_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "glyph": "👁️",
            "intent": "projection"
        },
        "access_control": {
            "entropy_gate": entropy_hash if entropy_hash else None,
            "allowed_observers": [observer_hash] if observer_hash else []
        },
        "is_avatar_projection": True
    }
    holograms.insert(0, avatar_projection)

    symbolic_grammar = generate_symbolic_light_grammar(operator_sequence)
    memory_echoes = [g for g in holograms if g.get("memory_echo")]

    ghx_meta = {
        "ghx_version": GHX_VERSION,
        "container_id": container_id,
        "generated": datetime.utcnow().isoformat(),
        "physics": container.get("physics", "symbolic-quantum"),
        "dimensions": 4,
        "holographic": True,
        "replay_enabled": True,
        "reversal_ready": True,
        "symbolic_light_grammar": symbolic_grammar,
        "avatar_projection": {
            "observer_id": observer_id,
            "observer_hash": observer_hash,
            "symbol": avatar_projection["symbol"],
            "entropy_verified": bool(entropy_hash)
        },
        "echoes": memory_echoes
    }

    if qglyph_string:
        qglyph = generate_qglyph_from_string(qglyph_string)
        ghx_meta.update({
            "linked_qglyph_id": qglyph.qglyph_id,
            "collapse_signature": qglyph.entropy_signature,
            "qentropy_lock": {
                "seed": entropy_seed,
                "entropy_hash": entropy_hash,
                "observer": observer_hash
            }
        })
    # 🔐 Inject Vault Signature Block
    from backend.modules.glyphvault.vault_key_manager import VaultKeyManager
    try:
        vault_origin_id = VaultKeyManager.get_public_id()
    except Exception:
        vault_origin_id = f"vault_{observer_hash}"

    ghx_meta["signed_by"] = vault_origin_id
    return {
        **ghx_meta,
        "holograms": holograms
    }

# Supporting functions remain unchanged
def generate_symbolic_light_grammar(sequence: List[str]) -> Dict[str, Any]:
    glyph_counts = Counter(sequence)
    grammar_string = "".join(s for s in sequence if s in ("↔", "⧖", "⬁", "→", "⊕", "🧠"))
    return {
        "grammar": grammar_string,
        "counts": dict(glyph_counts),
        "total": len(sequence),
        "operators_only": sum(glyph_counts[g] for g in ("↔", "⧖", "⬁", "→") if g in glyph_counts)
    }


def generate_light_logic(symbol: str) -> Dict[str, Any]:
    return {
        "color": glyph_color_map(symbol),
        "intensity": glyph_intensity_map(symbol),
        "animation": "pulse",
        "collapse_trace": symbol in ("⧖", "⬁")
    }


def generate_spatial_coordinates(glyph_id: str) -> Dict[str, float]:
    index = int(glyph_id[1:]) if glyph_id.startswith("g") and glyph_id[1:].isdigit() else 0
    return {
        "x": index * 2.0,
        "y": (index % 3) * 1.0,
        "z": (index // 3) * 1.5
    }


def glyph_color_map(symbol: str) -> str:
    return {
        "⊕": "#ffcc00",
        "↔": "#aa00ff",
        "⧖": "#00ffff",
        "🧠": "#00ff66",
        "⬁": "#ff6666",
        "→": "#66ccff"
    }.get(symbol, "#ffffff")


def glyph_intensity_map(symbol: str) -> float:
    return {
        "⊕": 0.9,
        "↔": 1.0,
        "⧖": 0.7,
        "🧠": 0.6,
        "⬁": 1.2,
        "→": 0.8
    }.get(symbol, 0.5)


def generate_narration(symbol: str, label: str) -> Dict[str, Any]:
    description_map = {
        "⊕": "Combine logic",
        "↔": "Entangled reasoning",
        "⧖": "Collapsed moment",
        "🧠": "Cognitive glyph",
        "⬁": "Mutation trigger",
        "→": "Directional execution"
    }
    spoken = description_map.get(symbol, f"Glyph {symbol}")
    return {
        "text_to_speak": f"{spoken}. {label}" if label else spoken,
        "voice": "default",
        "language": "en-US"
    }

def encode_ghx_from_scroll(scroll: dict) -> dict:
    """
    Converts a symbolic scroll (glyphs, entanglements, metadata) into GHX geometry format.

    Args:
        scroll (dict): The scroll object containing glyphs, entanglement, and metadata.

    Returns:
        dict: A GHX-encoded geometry payload for holographic visualization.
    """
    try:
        glyphs = scroll.get("glyphs", [])
        entangled = scroll.get("entangled", [])
        metadata = scroll.get("metadata", {})

        ghx_geometry = {
            "id": scroll.get("id", f"ghx_{int(time.time())}"),
            "glyphs": glyphs,
            "entangled": entangled,
            "geometry": metadata.get("geometry", "Tesseract 🧮"),
            "tags": metadata.get("tags", []),
            "entropy": metadata.get("entropy", 0.0),
            "timestamp": scroll.get("timestamp", time.time())
        }

        print(f"🎨 GHX encoded from scroll: {ghx_geometry['id']} "
              f"({len(glyphs)} glyphs, entangled={len(entangled)})")
        return ghx_geometry

    except Exception as e:
        print(f"❌ Failed to encode GHX from scroll: {e}")
        return {"error": str(e)}

def export_ghx(container: Dict[str, Any], output_path: str, qglyph_string: str = "", observer_id: str = "anon"):
    ghx_data = encode_glyphs_to_ghx(container, qglyph_string=qglyph_string, observer_id=observer_id)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ghx_data, f, indent=2)