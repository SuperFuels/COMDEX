# File: backend/modules/lean/lean_utils.py

import json
from typing import Dict, Any


def is_lean_container(container: Dict[str, Any]) -> bool:
    """
    Returns True if the container was imported from a Lean .lean file.
    """
    return container.get("metadata", {}).get("origin") == "lean_import"


def extract_theorems(container: Dict[str, Any]) -> list:
    """
    Returns a list of all symbolic theorems from the container.
    """
    return container.get("symbolic_logic", [])


def extract_lean_metadata(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns Lean-specific metadata fields from the container, if present.
    """
    meta = container.get("metadata", {})
    return {
        "origin": meta.get("origin"),
        "logic_type": meta.get("logic_type"),
        "source_path": meta.get("source_path")
    }


def get_theorem_names(container: Dict[str, Any]) -> list:
    """
    Returns a list of theorem names in the container.
    """
    logic = container.get("symbolic_logic", [])
    return [entry.get("name") for entry in logic if entry.get("symbol") == "⟦ Theorem ⟧"]


def summarize_lean_container(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a compact summary of a Lean container's logic structure.
    """
    return {
        "is_lean": is_lean_container(container),
        "source_path": container.get("metadata", {}).get("source_path"),
        "num_theorems": len(get_theorem_names(container)),
        "theorems": get_theorem_names(container)
    }


def pretty_print_lean_summary(container: Dict[str, Any]) -> None:
    """
    Prints a human-readable summary of Lean container contents.
    """
    summary = summarize_lean_container(container)
    print("\n📦 Lean Container Summary:")
    print(json.dumps(summary, indent=2))