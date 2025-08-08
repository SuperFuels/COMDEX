from backend.config import ENABLE_GLYPH_LOGGING

def safe_ghx_log(ghx, evt):
    """Safely send a GHX log event if logging is enabled and GHX object supports it."""
    if not ENABLE_GLYPH_LOGGING or ghx is None:
        return
    try:
        if hasattr(ghx, "log_event"):
            ghx.log_event(evt)
        elif hasattr(ghx, "append"):
            ghx.append(evt)
        elif hasattr(ghx, "publish"):
            ghx.publish(evt)
    except Exception:
        pass  # Do not break execution if logging fails