# ⬆️ Near the top of the file (after dotenv / os), add:
from backend.config import GLYPH_API_BASE_URL

...

# 🔄 Replace this original block:
# synth_response = requests.post(
#     "http://localhost:8000/api/aion/synthesize-glyphs",
#     json={"text": dream, "source": "reflection"}
# )

# ✅ With this updated version:
synth_response = requests.post(
    f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
    json={"text": dream, "source": "reflection"}
)
