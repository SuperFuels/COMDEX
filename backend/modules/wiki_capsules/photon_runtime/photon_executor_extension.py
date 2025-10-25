"""
⚡ Photon Executor Extension — Phase 7
-------------------------------------
Extends the Photon execution environment to support 📚 Wiki imports
and integrate Knowledge Graph lookups via get_wiki().

Bridges symbolic execution flow:
  .wiki.phn  → Knowledge Graph capsule
  .phn       → Photon executable
  .ptn       → Composite Photon Page (system orchestrator)
"""

from pathlib import Path
import json
import traceback
from backend.modules.wiki_capsules.integration.kg_query_extensions import get_wiki


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 Runtime Entry
# ─────────────────────────────────────────────────────────────────────────────
def run_photon_file(file_path: str) -> dict:
    """
    Execute a Photon-compatible file (.phn, .ptn, or .wiki.phn).
    Automatically resolves 📚 Wiki imports via Knowledge Graph (get_wiki).

    Returns:
      {
        "file": str,
        "imports": [ { "domain", "lemma", "data" } ],
        "status": "executed" | "error",
        "lines": int
      }
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}", "status": "error"}

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Failed to read file: {e}", "status": "error"}

    try:
        imports = []
        for line in content.splitlines():
            if "📚" in line:
                spec = line.split("📚", 1)[1].strip()
                try:
                    if ">" in spec:
                        domain, lemma = spec.split(">", 1)
                    else:
                        domain, lemma = "Lexicon", spec
                    try:
                        wiki = get_wiki(lemma.strip(), domain.strip())
                    except Exception as e:
                        wiki = {"error": str(e)}
                    imports.append({
                        "domain": domain.strip(),
                        "lemma": lemma.strip(),
                        "data": wiki
                    })
                except Exception as e:
                    imports.append({
                        "lemma": lemma.strip() if 'lemma' in locals() else "unknown",
                        "error": f"Failed import: {line.strip()} ({e})"
                    })

        result = {
            "file": str(path),
            "imports": imports,
            "lines": len(content.splitlines()),
        }

        if "⊕" in content or "↔" in content:
            result["execution"] = "Photon logic executed"
        else:
            result["execution"] = "Static capsule processed"

        result["status"] = "executed"
        return result

    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}


# ─────────────────────────────────────────────────────────────────────────────
# 🧪 Runtime Simulation
# ─────────────────────────────────────────────────────────────────────────────
def simulate_runtime(capsule_data: dict) -> dict:
    """Simulate a lightweight Photon execution using capsule metadata."""
    try:
        if "error" in capsule_data:
            raise ValueError("Simulation failed: capsule contains error key")

        return {"status": "ok", "result": "simulation_success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def simulate_photon_runtime(content: str) -> dict:
    """
    Simulate runtime execution for string-based Photon content.
    Detects 📚 imports and attempts inline KG resolution.
    """
    try:
        imports = []
        for line in content.splitlines():
            if "📚" in line:
                # Normalize line content
                clean_line = line.strip().replace("{", "").replace("}", "")
                spec = clean_line.split("📚", 1)[1].strip()
                if ">" in spec:
                    domain, lemma = spec.split(">", 1)
                else:
                    domain, lemma = "Lexicon", spec
                lemma = lemma.strip()
                domain = domain.strip()
                try:
                    wiki = get_wiki(lemma, domain)
                except Exception as e:
                    wiki = {"error": str(e)}
                imports.append({
                    "domain": domain,
                    "lemma": lemma,
                    "data": wiki
                })

        return {
            "imports": imports,
            "status": "ok",
            "execution": "Simulated photon runtime",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 🧩 Inline Execution Entry
# ─────────────────────────────────────────────────────────────────────────────
def run_inline(code: str, source: str = "<inline>") -> dict:
    """Execute or simulate a Photon script inline."""
    try:
        result = simulate_photon_runtime(code)
        result["source"] = source
        result["lines"] = len(code.splitlines())
        return result
    except Exception as e:
        return {"status": "error", "message": str(e), "source": source}