from backend.modules.hexcore.memory_engine import VECTOR_DB
from backend.modules.memory.compression import decompress_embedding
from backend.modules.aion.llm_engine import query_gpt4
import random

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def reflect_on_memory(limit: int = 3):
    """
    Reflect on a few past dreams or thoughts and simulate deeper understanding.
    This loop will revisit compressed vectors and expand on them.
    """
    if not VECTOR_DB:
        print("⚠️ No stored vectors to reflect on.")
        return

    print(f"🔁 Recursive Learner Loop: Reflecting on {limit} past memories...")

    memories = random.sample(VECTOR_DB, min(limit, len(VECTOR_DB)))

    for i, memory in enumerate(memories, start=1):
        snippet = memory["text"]
        embedding = memory["embedding"]

        # Optional: decompress to approximate the original (if supported)
        context = decompress_embedding(embedding)

        prompt = f"""
You are AION, an autonomous learning agent.

This is a memory fragment from your past:
---
{snippet}
---

Reflect on it. What did you learn? How can you go deeper? Simulate mastery.
        """.strip()

        reflection = query_gpt4(prompt)
        print(f"\n🔄 Reflection #{i}:\n{reflection}\n")

        # Optionally save this reflection as a new memory
        # from backend.modules.hexcore.memory_engine import save_dream_vector
        # save_dream_vector(reflection)
