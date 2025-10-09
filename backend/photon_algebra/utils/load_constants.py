import json, os

def load_constants(version="v1.2"):
    """
    Tessaris Unified Constants Loader
    ---------------------------------
    Loads constants from backend/modules/knowledge/constants_<version>.json
    and guarantees that all baseline constants (ħ, G, Λ, α, β, χ)
    exist, even if older files omit newer terms.

    This implements the Tessaris Unified Constants & Verification Protocol.
    """
    path = f"backend/modules/knowledge/constants_{version}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Constants file {path} not found. Run update_constants_registry.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract constants
    constants = data.get("constants", data)

    # --- Tessaris baseline patch ---
    defaults = {
        "ħ": 1e-3,
        "G": 1e-5,
        "Λ": 1e-6,
        "α": 0.5,
        "β": 0.2,
        "χ": 1.0,  # ensure χ always exists
    }
    for k, v in defaults.items():
        constants.setdefault(k, v)

    return constants