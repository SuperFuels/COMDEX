# backend/RQC/src/photon_runtime/telemetry/ghx_visualizer_sse.py
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from flask import Flask, Response, stream_with_context
from backend.RQC.src.photon_runtime.telemetry.ghx_awareness_feed import stream_sse

# ────────────────────────────────────────────────────────────────
# 🔹 Photon Encoder Hook (optional)
import os
try:
    from backend.RQC.src.photon_runtime.encoder import photon_encode
except ImportError:
    photon_encode = None

PHOTON_OUTPUT = os.getenv("PHOTON_OUTPUT", "false").lower() in ("1", "true", "yes")
# ────────────────────────────────────────────────────────────────

app = Flask(__name__)

# ────────────────────────────────────────────────────────────────
# Streaming wrapper: converts JSON/telemetry -> Photon glyphs
def photon_stream_wrapper():
    """Wrap the base telemetry stream with optional Photon encoding."""
    for event in stream_sse():
        if PHOTON_OUTPUT and photon_encode:
            try:
                yield photon_encode(event) + "\n"
            except Exception as e:
                yield f"[PhotonEncodingError] {e}\n"
        else:
            yield event + "\n"
# ────────────────────────────────────────────────────────────────

@app.route("/stream/ghx")
def stream():
    """
    SSE stream endpoint for GHX visualizer telemetry.
    Automatically emits Photon glyph telemetry if PHOTON_OUTPUT=true.
    """
    return Response(
        stream_with_context(photon_stream_wrapper()),
        mimetype="text/event-stream"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=False)