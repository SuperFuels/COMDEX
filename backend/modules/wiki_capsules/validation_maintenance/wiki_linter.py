"""
🧹 Wiki Linter — Unified Syntax and Metadata Validator
------------------------------------------------------
Validates .wiki.phn capsule syntax, YAML header integrity,
and field completeness before registration in the Knowledge Graph.
"""

from pathlib import Path
import yaml
import re

REQUIRED_FIELDS = ["lemma", "pos", "definitions"]
REQUIRED_META = ["version", "signed_by", "checksum"]


def lint_capsule_file(file_path: str) -> dict:
    """Run validation checks on a single .wiki.phn file."""
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "error": f"File not found: {file_path}"}

    try:
        text = path.read_text(encoding="utf-8")
        parsed = yaml.safe_load_all(text)
    except Exception as e:
        return {"status": "error", "error": f"YAML parse failed: {e}"}

    issues = []
    meta = {}
    content = {}

    # YAML streams (meta + content)
    for block in parsed:
        if not isinstance(block, dict):
            continue
        if "meta" in block:
            meta = block.get("meta", {})
        else:
            content = block

    # Meta checks
    for field in REQUIRED_META:
        if field not in meta:
            issues.append(f"Missing metadata field: {field}")

    # Field checks
    for field in REQUIRED_FIELDS:
        if field not in content:
            issues.append(f"Missing required field: {field}")

    # Lemma naming convention
    lemma = content.get("lemma", "")
    if lemma and not re.match(r"^[A-Za-z0-9_\-]+$", lemma):
        issues.append("Invalid lemma format (must be alphanumeric or underscore)")

    return {
        "status": "ok" if not issues else "warn",
        "file": file_path,
        "issues": issues,
        "meta": meta,
    }