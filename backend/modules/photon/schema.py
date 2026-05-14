from pathlib import Path
import json

_CANDIDATES = [
    Path(__file__).with_name("photon_capsule_schema.json"),               # backend/modules/photon/photon_capsule_schema.json
    Path(__file__).parent.parent / "photonlang" / "photon_capsule_schema.json",  # fallback
]

def load_photon_capsule_schema() -> dict:
    for p in _CANDIDATES:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        "photon_capsule_schema.json not found in: " + ", ".join(map(str, _CANDIDATES))
    )