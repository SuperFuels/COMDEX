"""
Tessaris Validation & Maintenance Suite - Phase 6
-------------------------------------------------
Performs unified validation across .wiki.phn capsules and Knowledge Graph.

Modules included:
 - wiki_linter.py           -> syntax + metadata validation
 - reference_validator.py   -> cross-link & KG reference integrity
 - maintenance_jobs.py      -> orchestration & nightly routines
 - tests/test_validation_suite.py  -> end-to-end chain tests
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

#───────────────────────────────────────────────
# wiki_linter.py
#───────────────────────────────────────────────

class WikiLinter:
    """Validate .wiki.phn capsule syntax and metadata consistency."""
    REQUIRED_META = ["version", "signed_by", "checksum"]

    def __init__(self, base_path: str = "data/knowledge"):
        self.base_path = Path(base_path)

    def _load_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def _extract_meta(self, text: str) -> Dict[str, str]:
        meta_match = re.search(r"meta:\s*(.*?)\n\n", text, re.DOTALL)
        if not meta_match:
            return {}
        meta_block = meta_match.group(1)
        meta = {}
        for line in meta_block.splitlines():
            if ":" in line:
                k, v = [s.strip() for s in line.split(":", 1)]
                meta[k] = v
        return meta

    def _compute_checksum(self, text: str) -> str:
        return hashlib.sha3_256(text.encode("utf-8")).hexdigest()

    def validate_capsule(self, path: Path) -> Dict[str, Any]:
        result = {"file": str(path), "errors": [], "warnings": []}
        try:
            text = self._load_file(path)
        except Exception as e:
            result["errors"].append(f"Failed to read: {e}")
            return result

        # Metadata
        meta = self._extract_meta(text)
        for field in self.REQUIRED_META:
            if field not in meta:
                result["errors"].append(f"Missing meta field: {field}")

        # Checksum consistency
        if "checksum" in meta:
            calc = self._compute_checksum(text)
            if meta["checksum"] != calc:
                result["errors"].append("Checksum mismatch")

        # Structural validation
        if not re.search(r"lemma:", text):
            result["warnings"].append("Missing lemma section")
        if not re.search(r"definitions:", text):
            result["warnings"].append("Missing definitions block")

        return result

    def run_all(self) -> Dict[str, Any]:
        all_results = {"passed": 0, "failed": 0, "warnings": 0, "results": []}
        for path in self.base_path.rglob("*.wiki.phn"):
            res = self.validate_capsule(path)
            all_results["results"].append(res)
            if res["errors"]:
                all_results["failed"] += 1
            elif res["warnings"]:
                all_results["warnings"] += 1
            else:
                all_results["passed"] += 1
        return all_results


#───────────────────────────────────────────────
# reference_validator.py
#───────────────────────────────────────────────

class ReferenceValidator:
    """Cross-link and Knowledge Graph reference checker."""

    def __init__(self, kg_registry: str = "data/knowledge/kg_registry.json"):
        self.kg_path = Path(kg_registry)
        self.registry = json.load(open(self.kg_path)) if self.kg_path.exists() else {}

    def validate_links(self) -> List[str]:
        errors = []
        for domain, entries in self.registry.items():
            for lemma, entry in entries.items():
                entangled = entry.get("meta", {}).get("entangled_links", {})
                if isinstance(entangled, dict):
                    for ref_domain, targets in entangled.items():
                        for target in targets:
                            if target not in self.registry.get(ref_domain, {}):
                                errors.append(
                                    f"Broken reference: {domain}>{lemma} -> {ref_domain}>{target}"
                                )
        return errors


#───────────────────────────────────────────────
# maintenance_jobs.py
#───────────────────────────────────────────────

class MaintenanceJobs:
    """Nightly orchestration: linting + cross-ref validation."""

    def __init__(self):
        self.linter = WikiLinter()
        self.ref_validator = ReferenceValidator()

    def run_full_validation(self) -> Dict[str, Any]:
        results = self.linter.run_all()
        ref_errors = self.ref_validator.validate_links()

        results["cross_link_errors"] = len(ref_errors)
        results["ref_errors_list"] = ref_errors
        if ref_errors:
            results["failed"] += len(ref_errors)
        return results

    def report_summary(self, results: Dict[str, Any]):
        print("\n── Tessaris Validation Summary ──")
        print(f"✅ Passed: {results['passed']}")
        print(f"⚠️  Warnings: {results['warnings']}")
        print(f"❌ Failed: {results['failed']}")
        if results.get("cross_link_errors"):
            print(f"🔗 Broken links: {results['cross_link_errors']}")
        print("──────────────────────────────────\n")


#───────────────────────────────────────────────
# CLI Interface (manual run)
#───────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Tessaris Wiki Validation Suite")
    parser.add_argument("--check-all", action="store_true", help="Run full validation")
    args = parser.parse_args()

    jobs = MaintenanceJobs()
    results = jobs.run_full_validation()
    jobs.report_summary(results)

    if results["failed"] > 0:
        exit(1)
    else:
        exit(0)


#───────────────────────────────────────────────
# tests/test_validation_suite.py
#───────────────────────────────────────────────

import pytest
from pathlib import Path
import tempfile

def _make_fake_capsule(path: Path, meta_ok=True):
    content = "meta:\n"
    if meta_ok:
        checksum = "abc123"
        content += f"  version: 1.0\n  signed_by: Tessaris-Core\n  checksum: {checksum}\n\n"
    else:
        content += "\n"
    content += "lemma: Apple\ndefinitions:\n- A fruit\n"
    path.write_text(content, encoding="utf-8")

@pytest.fixture
def temp_knowledge_dir(tmp_path):
    data = tmp_path / "Lexicon"
    data.mkdir(parents=True)
    _make_fake_capsule(data / "Apple.wiki.phn", meta_ok=True)
    _make_fake_capsule(data / "Banana.wiki.phn", meta_ok=False)
    return tmp_path

def test_linter_strict_fail(temp_knowledge_dir):
    linter = WikiLinter(base_path=temp_knowledge_dir)
    results = linter.run_all()
    assert results["failed"] > 0
    assert any("Missing meta field" in e for r in results["results"] for e in r["errors"])

def test_reference_validator_detects_broken_links(tmp_path):
    kg = tmp_path / "kg_registry.json"
    data = {"Lexicon": {"apple": {"meta": {"entangled_links": {"Lexicon": ["missing"]}}}}}
    kg.write_text(json.dumps(data), encoding="utf-8")
    rv = ReferenceValidator(kg_registry=str(kg))
    errors = rv.validate_links()
    assert "Broken reference" in errors[0]

def test_maintenance_job_summary(temp_knowledge_dir):
    jobs = MaintenanceJobs()
    jobs.linter.base_path = temp_knowledge_dir
    res = jobs.run_full_validation()
    assert "passed" in res and "failed" in res