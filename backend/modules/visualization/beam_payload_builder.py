# ✅ File: backend/modules/visualization/beam_payload_builder.py

import random
from typing import List, Dict, Any
import uuid

# ✅ QWave Transfer Hook
from backend.modules.qwave.qwave_transfer_sender import send_qwave_transfer


# 🔧 Logic Packet Builder
def build_logic_packet(source_id: str, target_id: str) -> Dict[str, Any]:
    return {
        "packet_id": str(uuid.uuid4()),
        "source_node": source_id,
        "target_node": target_id,
        "trace_direction": random.choice(["backward", "forward"]),
        "infer_depth": random.randint(1, 3),
        "cause": random.choice(["triggered", "mutation", "observer_reflex", "goal_match"]),
        "intent": random.choice(["optimize", "contrast", "verify", "explore"]),
        "prediction": random.choice(["likely success", "uncertain", "conflict", "high potential"]),
    }


# 🌐 Example Glyph Node Generator
def generate_test_glyph_nodes(count: int = 8) -> List[Dict[str, Any]]:
    glyphs = []
    for i in range(count):
        glyph = {
            "id": f"glyph-{i}",
            "label": f"G{i}",
            "position": [
                round(random.uniform(-5, 5), 2),
                round(random.uniform(-5, 5), 2),
                round(random.uniform(-1, 1), 2),
            ],
            "predicted": random.random() > 0.5,
            "goalMatchScore": round(random.uniform(0, 1), 2),
            "rewriteSuccessProb": round(random.uniform(0, 1), 2),
            "entropy": round(random.uniform(0, 3), 2),
            "collapse_state": random.choice(["collapsed", "predicted", "contradicted", None]),
            "trailId": f"trail-{random.randint(1, 3)}",
            "node_type": random.choice(["glyph", "atom", "electron"]),
            "tick": i,
        }
        glyphs.append(glyph)
    return glyphs


# 💡 QWave Beam Generator with Logic Packets
def generate_test_beams(glyphs: List[Dict[str, Any]], container_id: str = "test_container") -> List[Dict[str, Any]]:
    beams = []
    for i in range(len(glyphs) - 1):
        source = glyphs[i]
        target = glyphs[i + 1]

        beam_type = random.choice(["entangled", "causal", "teleport", "prediction"])
        collapse_state = source.get("collapse_state") or target.get("collapse_state")

        beam = {
            "id": str(uuid.uuid4()),
            "source": source["position"],
            "target": target["position"],
            "type": beam_type,
            "collapse_state": collapse_state,
            "predicted": source["predicted"] or target["predicted"],
            "sqiScore": round(max(
                source.get("goalMatchScore", 0),
                source.get("rewriteSuccessProb", 0),
                target.get("goalMatchScore", 0),
                target.get("rewriteSuccessProb", 0),
            ), 2),
            "qwave": {
                "emotion": random.choice(["curiosity", "urgency", "neutral", "wonder"]),
                "memory_weight": round(random.uniform(0.1, 1.0), 2),
                "logic_packet": build_logic_packet(source["id"], target["id"])
            }
        }

        beams.append(beam)

        # ✅ Realtime QWave Transfer for each beam
        try:
            send_qwave_transfer(container_id, source="beam_payload_builder", beam_data=beam)
        except Exception as e:
            print(f"[BeamPayloadBuilder] ⚠️ QWave transfer failed for beam {beam['id']}: {e}")

    return beams


# 🔧 Combined Beam + Glyph Data
def build_test_beam_payload(count: int = 8, container_id: str = "test_container") -> Dict[str, Any]:
    glyphs = generate_test_glyph_nodes(count)
    beams = generate_test_beams(glyphs, container_id=container_id)
    return {
        "glyphs": glyphs,
        "beams": beams
    }