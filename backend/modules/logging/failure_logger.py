import os
from dotenv import load_dotenv

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Load .env for toggle
load_dotenv()
DISABLE_FAILURE_GLYPHS = os.getenv("DISABLE_FAILURE_GLYPHS", "false").lower() == "true"

class FailureLogger:
    def __init__(self):
        self.kg_writer = None
        self.disable_glyphs = DISABLE_FAILURE_GLYPHS

    def log_failure(self, failure_type, message, context=None):
        print(f"❌ Failure logged: {failure_type} - {message} | Context: {context}")

        if self.disable_glyphs:
            print("🚫 Failure glyph injection disabled by toggle.")
            return

        try:
            # ✅ Defer import until needed (avoids circular import)
            if self.kg_writer is None:
                from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
                self.kg_writer = get_kg_writer()

            self.kg_writer.inject_glyph(
                content=message,
                glyph_type="failure",
                metadata={
                    "type": failure_type,
                    "origin": context or "system",
                    "tags": ["📉", "🧠"],
                },
                plugin="FailureLogger"
            )
            print(f"📦 Injected failure glyph: {failure_type} - {message}")
        except Exception as e:
            print(f"⚠️ Failed to inject failure glyph into KG: {e}")