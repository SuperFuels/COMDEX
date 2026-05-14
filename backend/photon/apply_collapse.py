from backend.photon.validator import validate_glyphs

def collapse_or_error(glyphs):
    errors = validate_glyphs(glyphs)
    if errors:
        return {"status": "error", "errors": errors}
    return {"status": "ok", "glyphs": glyphs}