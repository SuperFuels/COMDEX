"""
🧩 Wiki Linter - Phase 6
------------------------
Validates `.wiki.phn` capsules for syntax + metadata completeness.
"""

from pathlib import Path
from typing import List, Dict, Any
import yaml, re, sys, json

REQUIRED_META_FIELDS = ["version", "signed_by", "checksum"]
REQUIRED_FIELDS = ["lemma", "definitions", "examples"]


def lint_capsule(file_path: Path) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "file": str(file_path),
        "errors": [],
        "warnings": [],
        "meta": {},
        "valid": False,
        "status": "error",
    }

    if not file_path.exists():
        report["errors"].append("File not found.")
        return report

    try:
        text = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except Exception as e:
        report["errors"].append(f"YAML parse failed: {e}")
        return report

    if not isinstance(data, dict):
        report["errors"].append("Invalid YAML structure.")
        return report

    # ─── Extract meta and content ─────────────────────────────
    meta = data.get("meta", {})
    content = {k: v for k, v in data.items() if k != "meta"}

    # Accept top-level meta fields as implicit meta
    for key in REQUIRED_META_FIELDS:
        if key in content and key not in meta:
            meta[key] = content[key]

    # Meta presence
    if not meta:
        report["errors"].append("Missing 'meta:' header block.")

    # Meta completeness
    for key in REQUIRED_META_FIELDS:
        if key not in meta or meta[key] in (None, "", []):
            report["errors"].append(f"Missing metadata field: {key}")

    # Required content fields
    for key in REQUIRED_FIELDS:
        if key not in content:
            report["errors"].append(f"Missing required field: {key}")

    # Lemma format
    lemma = content.get("lemma", "")
    if lemma and not re.match(r"^[A-Za-z0-9_\- ]+$", str(lemma)):
        report["errors"].append(f"Invalid lemma format: '{lemma}'")

    # Finalize
    report["meta"] = meta
    report["valid"] = len(report["errors"]) == 0
    report["status"] = "ok" if report["valid"] else "error"

    return report


def lint_directory(path: str | Path) -> List[Dict[str, Any]]:
    base = Path(path)
    results = []
    for f in base.rglob("*.wiki.phn"):
        results.append(lint_capsule(f))
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wiki_linter.py <directory>")
        sys.exit(1)
    target = Path(sys.argv[1])
    if not target.exists():
        print(f"❌ Directory not found: {target}")
        sys.exit(1)
    print(json.dumps(lint_directory(target), indent=2, ensure_ascii=False))