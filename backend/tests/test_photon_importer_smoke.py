# backend/tests/test_photon_importer_smoke.py
import sys
import importlib
import importlib.util as ilu
from pathlib import Path

# --- repo root on sys.path ---
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- install Photon importer (FileFinder hook) ---
from backend.modules.photonlang.importer import install as _photon_install
_photon_install()

def _hook_present() -> bool:
    return any(getattr(h, "_tessaris_photon_hook", False) for h in sys.path_hooks)

def _flush_importer_cache_for(path: Path) -> None:
    """Force Python to rebuild FileFinder for this path with our new hook."""
    p = str(path)
    sys.path_importer_cache.pop(p, None)

# Invalidate module finders **and** drop stale FileFinders for our dirs
import importlib as _il
_il.invalidate_caches()
_flush_importer_cache_for(ROOT)
_flush_importer_cache_for(ROOT / "backend")
_flush_importer_cache_for(ROOT / "backend" / "tests")

# Also clear any cached finders for package paths under backend.__path__
try:
    import backend  # ensures package is loaded and __path__ is available
    for p in list(getattr(backend, "__path__", [])):
        sys.path_importer_cache.pop(str(p), None)
except Exception:
    pass
_il.invalidate_caches()

# Make sure test package markers exist (safe if they already exist)
for pkg in (ROOT / "backend/__init__.py", ROOT / "backend/tests/__init__.py"):
    if not pkg.exists():
        pkg.parent.mkdir(parents=True, exist_ok=True)
        pkg.write_text("", encoding="utf-8")
        _flush_importer_cache_for(pkg.parent)
_il.invalidate_caches()

def test_hook_installs_idempotently():
    assert _hook_present() is True
    # Idempotent re-install should remain True
    assert _photon_install() is True
    assert _hook_present() is True

def test_import_and_run_demo_math():
    # Assert the import is resolvable (helps diagnose early)
    spec = ilu.find_spec("backend.tests.demo_math")
    assert spec is not None, "Spec not found for backend.tests.demo_math"

    m = importlib.import_module("backend.tests.demo_math")
    out = m.add_and_measure(2, 3)

    assert isinstance(out, dict)
    assert out["z"] == 5
    assert isinstance(out["m"], dict)
    assert out["m"].get("value") == 5