import yaml
from pathlib import Path
from backend.modules.aion_resonance import telemetry, memory

PRIMITIVES_FILE = Path(__file__).parent / "primitives.yaml"

with open(PRIMITIVES_FILE) as f:
    PRIMITIVES = yaml.safe_load(f)

def generate_phi(intent: str):
    phi = PRIMITIVES.get(intent, PRIMITIVES["ack"])
    telemetry.log_phi_event(intent, phi)
    memory.store_phi_mapping(intent, phi)
    return phi