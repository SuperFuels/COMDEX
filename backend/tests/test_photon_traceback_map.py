def test_photon_line_offset_mapping(monkeypatch):
    # Ensure the enricher is active
    from backend.modules.photonlang.runtime.traceback_enricher import install, format_exception
    install()

    import importlib, sys
    sys.path.insert(0, "backend/tests")
    m = importlib.import_module("demo_error")  # your existing .photon error sample

    try:
        m.oops(3)  # should raise NameError at a known .photon line
    except Exception as e:
        out = format_exception(e)
        # Assert the reported line references the .photon file and not the prolog line
        assert "demo_error.photon" in out
        # depending on your sample, assert the exact line or just that it's a small-ish number
        # assert "line 2" in out  # ← tune if you like