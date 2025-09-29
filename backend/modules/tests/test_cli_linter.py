import io
import sys
import contextlib
import pytest

import backend.tools.cli_linter as cli


def run_cli(argv, input_text=None):
    """Helper to run CLI and capture output deterministically."""
    out_buf, err_buf = io.StringIO(), io.StringIO()

    # Simulate stdin if needed
    if input_text is not None:
        sys.stdin = io.StringIO(input_text)

    code = None
    with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
        try:
            code = cli.main(argv)
        except SystemExit as e:
            code = e.code

    sys.stdin = sys.__stdin__  # reset stdin

    return code, out_buf.getvalue(), err_buf.getvalue()


# --- Tests ---
def test_cli_ok(tmp_path):
    glyph_file = tmp_path / "ok.glyph"
    glyph_file.write_text("⟦ Logic | Test: A → B ⟧", encoding="utf-8")

    code, out, err = run_cli([str(glyph_file)])
    assert code == 0
    assert "✅ OK" in out


def test_cli_collision_detected(tmp_path):
    glyph_file = tmp_path / "collision.glyph"
    glyph_file.write_text("⟦ Logic | Test: X → ⊕(A, B) ⟧", encoding="utf-8")

    code, out, err = run_cli([str(glyph_file)])
    assert code != 0
    assert "⚠️ Collision" in out


def test_cli_alias_detected(tmp_path):
    glyph_file = tmp_path / "alias.glyph"
    glyph_file.write_text("⟦ Quantum | Test: ⊕_q(A, B) ⟧", encoding="utf-8")

    code, out, err = run_cli([str(glyph_file)])
    assert code != 0
    assert "Alias used" in out


def test_cli_stdin_ok():
    code, out, err = run_cli(["-"], input_text="⟦ Logic | Test: A → B ⟧")
    assert code == 0
    assert "✅ OK" in out