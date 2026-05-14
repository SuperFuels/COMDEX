import subprocess
import sys
import tempfile
import pathlib
import json


def _make_temp_container():
    """Create a minimal container.json file."""
    data = {
        "type": "dc",
        "id": "test-container",
        "symbolic_logic": [
            {"name": "A_implies_B", "symbol": "⊢", "logic": "A -> B"}
        ],
    }
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp_path = pathlib.Path(tmp.name)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return tmp_path


def _make_dummy_lean(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a dummy .lean file."""
    lean_file = tmp_path / "dummy.lean"
    lean_file.write_text("theorem foo : True := trivial\n")
    return lean_file


def test_inject_png_out(tmp_path):
    """Check `inject` runs with --png-out (PNG or fallback .mmd)."""
    container = _make_temp_container()
    lean_file = _make_dummy_lean(tmp_path)
    out_png = tmp_path / "out.png"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.modules.lean.lean_inject_cli",
            "inject",
            str(container),
            str(lean_file),
            "--png-out",
            str(out_png),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    # Either PNG or Mermaid fallback should exist
    if out_png.exists():
        text = out_png.read_bytes()
        assert len(text) > 0
    else:
        alt_mmd = out_png.with_suffix(".mmd")
        assert alt_mmd.exists()
        text = alt_mmd.read_text()
        assert "graph" in text or "mermaid" in text