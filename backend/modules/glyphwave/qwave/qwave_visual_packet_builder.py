from typing import Dict, Any
import uuid
import random
import time


# Emotion / logic / memory modulation types for demo purposes
QWAVE_TYPES = ["emotion", "memory", "logic", "intuition", "dream"]


# Basic symbolic beam builder

def build_qwave_visual_packet(
    source_id: str,
    target_id: str,
    carrier_type: str = "qwave",
    coherence: float = None,
    entangled_path: str = None,
    modulation_strategy: str = None,
    emotion_type: str = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Build a symbolic QWave beam visual packet for QFC rendering.
    """
    coherence = coherence if coherence is not None else round(random.uniform(0.7, 1.0), 3)
    beam_id = str(uuid.uuid4())
    modulation_strategy = modulation_strategy or random.choice(QWAVE_TYPES)
    emotion_type = emotion_type or random.choice(["joy", "focus", "curiosity", "chaos"])

    return {
        "id": beam_id,
        "source": source_id,
        "target": target_id,
        "carrier_type": carrier_type,
        "coherence": coherence,
        "entangled_path": entangled_path or f"{source_id}↔{target_id}",
        "modulation_strategy": modulation_strategy,
        "emotion": emotion_type,
        "timestamp": time.time(),
        "metadata": metadata or {},
    }