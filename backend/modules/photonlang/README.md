# Photon Importer — Environment Flags

- `PHOTON_IMPORT=1`  
  Auto-installs the Photon importer via the runtime wrapper
  (`from backend.modules.photonlang.runtime import photon_importer; photon_importer.install()`).

- `PHOTON_IMPORT_BYPASS=1`  
  Compiles raw `.photon` text without expanding glyphs (debug only).

- `PHOTON_IMPORT_STRICT=1`  
  Raises `SyntaxError` if any code-glyphs remain after expansion.

Typical run:

```bash
PHOTON_IMPORT=1 PYTHONPATH=. python -c "from backend.modules.photonlang.runtime import photon_importer; photon_importer.install(); import demo; demo.hello()"

---

# 3) QoL CLI shims

Run these via `python -m ...` (no packaging needed).

## File: `backend/modules/photonlang/cli/__init__.py`
```python
# empty on purpose


Examples; # Compress
PYTHONPATH=. python -m backend.modules.photonlang.cli.compress path/to/file.py

# Expand
PYTHONPATH=. python -m backend.modules.photonlang.cli.expand path/to/file.photon

# Run from compressed (importer auto-installed)
PYTHONPATH=. python -m backend.modules.photonlang.cli.run demo --call hello


⸻

5) Editor support (pointer)

Add a short note in README.md linking to a basic VS Code tmLanguage.json later (tokenize your glyph set and colorize). Not required for functionality.