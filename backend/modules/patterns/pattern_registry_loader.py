# File: backend/modules/patterns/pattern_registry_loader.py
# 📦 Loads the pattern registry JSON for symbolic spreadsheet + pattern engine

import json
import os
from typing import List, Dict, Any

# Absolute path to the pattern registry
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../../data/patterns/pattern_registry.json"))

def load_pattern_registry() -> List[Dict[str, Any]]:
    """
    Loads the pattern registry from backend/data/patterns/pattern_registry.json.
    Raises FileNotFoundError if the file is missing.
    """
    if not os.path.exists(REGISTRY_PATH):
        raise FileNotFoundError(f"Pattern registry not found at {REGISTRY_PATH}")
    
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)