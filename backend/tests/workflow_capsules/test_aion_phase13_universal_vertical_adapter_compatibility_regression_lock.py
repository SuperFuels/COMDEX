from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CANDIDATE_GLOBS = [
    'backend/modules/aion_gateway/*.py',
    'backend/tests/workflow_capsules/test_aion_*vertical*.py',
    'backend/tests/workflow_capsules/test_aion_*parallel*.py',
    'backend/tests/workflow_capsules/test_aion_*catalog*.py',
    'docs/rfc/*vertical*.tex',
    'docs/rfc/*parallel*.tex',
    'docs/rfc/*catalog*.tex',
]
REQUIRED_TERMS = [
    'vertical',
    'home_fixed',
]
OPTIONAL_TERMS = [
    'home_repair',
    'adapter',
    'catalog',
    'capability',
    'parallel',
]
FORBIDDEN_TERMS = [
    'costa_connect',
    'costa_conexion',
    'hardcoded_costa',
    '"vertical_key": null',
    '"business_id": null',
]


def _candidate_files():
    files = []
    for pattern in CANDIDATE_GLOBS:
        files.extend(ROOT.glob(pattern))

    excluded_names = {
        Path(__file__).name,
        Path(__file__).name.replace("_lock.py", "_lock_doc.py"),
    }

    return sorted({
        p
        for p in files
        if p.is_file()
        and "__pycache__" not in str(p)
        and p.name not in excluded_names
        and "aion_phase13_" not in p.name
    })


def _combined_text():
    return "\n".join(p.read_text(errors="ignore").lower() for p in _candidate_files())


def test_phase13_universal_vertical_adapter_compatibility_candidate_files_exist():
    assert _candidate_files(), "No candidate files found for Universal Vertical Adapter Compatibility regression lock"


def test_phase13_universal_vertical_adapter_compatibility_required_terms_exist():
    text = _combined_text()
    for term in REQUIRED_TERMS:
        assert term in text


def test_phase13_universal_vertical_adapter_compatibility_has_at_least_one_adapter_specific_term():
    text = _combined_text()
    assert any(term in text for term in OPTIONAL_TERMS)


def test_phase13_universal_vertical_adapter_compatibility_does_not_introduce_forbidden_live_or_random_boundary():
    text = _combined_text()
    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in text


def test_phase13_universal_vertical_adapter_compatibility_lock_is_repository_grounded():
    paths = [str(p.relative_to(ROOT)).lower() for p in _candidate_files()]
    joined = "\n".join(paths)
    assert "backend/modules/aion_gateway" in joined or "backend/tests/workflow_capsules" in joined
