"""
🧩 Photon Page Validator
------------------------
Validates syntax, imports, and entanglement rules for .ptn capsules.
"""

from backend.modules.wiki_capsules.photon_page.photon_page_spec import PhotonPage
from pathlib import Path

def validate_syntax(page: PhotonPage) -> bool:
    if not page.name or not isinstance(page.name, str):
        raise ValueError("PhotonPage must have a valid name.")
    if "⊕" in page.body or "↔" in page.body or "∇" in page.body:
        return True  # contains valid Photon operators
    if not page.body.strip():
        raise ValueError("PhotonPage body cannot be empty.")
    return True

def validate_imports(page: PhotonPage, wiki_root: Path) -> bool:
    for imp in page.imports:
        file_path = wiki_root / f"{imp.title()}.wiki.phn"
        if not file_path.exists():
            raise FileNotFoundError(f"Missing import: {file_path}")
    return True

def validate_entanglement(page: PhotonPage) -> bool:
    # Example entanglement rule: must not reference itself
    if page.name in page.imports:
        raise ValueError(f"PhotonPage {page.name} cannot import itself.")
    return True

def validate_page(page: PhotonPage, wiki_root: Path) -> bool:
    return (
        validate_syntax(page)
        and validate_imports(page, wiki_root)
        and validate_entanglement(page)
    )