import json
import os
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ✅ Index + Glyph Injection
from backend.modules.knowledge_graph.indexes import curiosity_index
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter

# ✅ Paths
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")
INFERENCE_LOG = os.path.join(os.path.dirname(__file__), "aion_inference_chain.log")

# 🧠 Curiosity Chain — symbolic next steps per learned tag
CURIOSITY_CHAIN = {
    "communication": ["public speaking", "negotiation"],
    "logic": ["formal logic", "systems thinking"],
    "planning": ["project management", "prioritization"],
    "ethics": ["moral philosophy", "bioethics"],
    "observation": ["pattern recognition", "scientific method"],
    "emotion": ["empathy", "emotional regulation"],
    "creativity": ["design thinking", "visual storytelling"],
    "language": ["storytelling", "rhetoric"],
    "self-awareness": ["metacognition", "personal growth"],
    "problem solving": ["debugging", "hypothesis testing"]
}

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_inference(skill_from, skill_to):
    with open(INFERENCE_LOG, "a") as log:
        log.write(f"[{datetime.utcnow().isoformat()}] 🧠 AION inferred: '{skill_from}' → '{skill_to}'\n")

def run_inference():
    memory = load_memory()
    learned_titles = {s["title"] for s in memory if s.get("status") == "learned"}
    existing_titles = {s["title"] for s in memory}

    writer = KnowledgeGraphWriter()
    added_count = 0

    for skill in memory:
        if skill.get("status") == "learned":
            for tag in skill.get("tags", []):
                next_skills = CURIOSITY_CHAIN.get(tag.lower(), [])
                for new_title in next_skills:
                    if new_title not in existing_titles:
                        new_entry = {
                            "title": new_title,
                            "tags": [tag],
                            "status": "queued",
                            "source": "inference_engine",
                            "added_on": datetime.utcnow().isoformat()
                        }
                        memory.append(new_entry)
                        log_inference(skill["title"], new_title)
                        added_count += 1

                        # ✅ Inject into curiosity_index
                        curiosity_index.add_inferred_skill(
                            title=new_title,
                            tag=tag,
                            inferred_from=skill["title"]
                        )

                        # ✅ Inject as symbolic glyph into .dc container
                        writer.inject_glyph(
                            content=new_title,
                            glyph_type="inferred_skill",
                            metadata={
                                "tags": [tag],
                                "inferred_from": skill["title"]
                            },
                            forecast_confidence=0.85,
                            plugin="curiosity_engine"
                        )

    if added_count > 0:
        save_memory(memory)
        print(f"🔁 Inferred and queued {added_count} new skills.")
    else:
        print("ℹ️ No new inferences made.")

if __name__ == "__main__":
    run_inference()