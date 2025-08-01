"""
rubric_utils.py

🔍 Design Rubric Compliance Checker
Auto-scans Python modules and `.dc.json` containers to verify:
- 🔁 Deduplication Logic
- 📦 Container Awareness
- 🧠 Semantic Metadata
- ⏱️ Timestamps (ISO 8601)
- 🧩 Plugin Compatibility
- 🔍 Search & Summary API
- 📊 Readable + Compressed Export
- 📚 .dc Container Injection
"""

import os
import ast
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

REQUIRED_KEYS = [
    "🔁", "📦", "🧠", "⏱️", "🧩", "🔍", "📊", "📚"
]

# ✅ Added utility functions for KnowledgeGraphWriter
def generate_uuid() -> str:
    """
    Generates a unique UUID string.
    """
    return str(uuid.uuid4())

def get_current_timestamp() -> str:
    """
    Returns the current UTC timestamp in ISO 8601 format.
    """
    return datetime.utcnow().isoformat()

def check_rubric_in_docstring(file_path: str) -> Dict:
    """Scans a .py file for rubric checklist in the top-level docstring."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        mod = ast.parse(source)
        doc = ast.get_docstring(mod) or ""

        found = {key: (key in doc) for key in REQUIRED_KEYS}
        result = _evaluate_result(found)
        return {"status": result, "missing": [k for k, v in found.items() if not v]}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def check_rubric_in_dc_json(file_path: str) -> Dict:
    """Scans a .dc.json container for presence of rubric-related structures."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        checks = {
            "📦": "container_id" in data,
            "🧠": "metadata" in data or "glyphs" in data,
            "⏱️": any("timestamp" in g for g in data.get("glyphs", [])),
            "📚": "glyphs" in data,
            "📊": isinstance(data.get("glyphs"), list),
        }

        for key in REQUIRED_KEYS:
            checks.setdefault(key, False)

        result = _evaluate_result(checks)
        return {"status": result, "missing": [k for k, v in checks.items() if not v]}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def _evaluate_result(flags: Dict[str, bool]) -> str:
    missing = sum(1 for v in flags.values() if not v)
    if missing == 0:
        return "PASS"
    elif missing <= 2:
        return "WARN"
    else:
        return "FAIL"

def validate_file(file_path: str) -> Dict:
    """Main entrypoint — automatically picks parser based on file type."""
    if file_path.endswith(".py"):
        return check_rubric_in_docstring(file_path)
    elif file_path.endswith(".dc.json"):
        return check_rubric_in_dc_json(file_path)
    else:
        return {"status": "SKIP", "reason": "Unsupported file type"}

# Optional: Hook-in broadcast or logging
def emit_violation_event(file_path: str, result: Dict, broadcast: bool = False):
    if result["status"] == "FAIL":
        msg = f"[RUBRIC] ❌ {file_path} failed Design Rubric. Missing: {result.get('missing', [])}"
        if broadcast:
            # Integrate into GlyphNet broadcast stream if needed
            from backend.modules.glyphnet.glyphnet_ws import broadcast_symbolic_event
            broadcast_symbolic_event({
                "type": "rubric_violation",
                "data": {"file": file_path, "missing": result.get("missing", [])}
            })
        else:
            print(msg)