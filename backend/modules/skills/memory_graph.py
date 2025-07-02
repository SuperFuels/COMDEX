import json
import os
from collections import defaultdict

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")
GRAPH_FILE = os.path.join(os.path.dirname(__file__), "memory_graph.json")

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def build_graph(memory_entries):
    graph = {
        "nodes": [],
        "edges": []
    }
    node_ids = {}
    next_id = 0

    tag_to_skills = defaultdict(list)

    # Add skill nodes
    for entry in memory_entries:
        skill_title = entry["title"]
        tags = entry.get("tags", [])
        node_ids[skill_title] = next_id
        graph["nodes"].append({"id": next_id, "label": skill_title, "type": "skill"})
        skill_id = next_id
        next_id += 1

        for tag in tags:
            tag_to_skills[tag].append(skill_title)

    # Add tag nodes and edges
    for tag, skills in tag_to_skills.items():
        tag_id = next_id
        node_ids[tag] = tag_id
        graph["nodes"].append({"id": tag_id, "label": tag, "type": "tag"})
        next_id += 1

        for skill in skills:
            graph["edges"].append({
                "source": node_ids[skill],
                "target": tag_id,
                "type": "tagged_with"
            })

    return graph

def save_graph(graph):
    with open(GRAPH_FILE, "w") as f:
        json.dump(graph, f, indent=2)
    print(f"✅ Memory graph saved to {GRAPH_FILE}")

if __name__ == "__main__":
    memory = load_memory()
    graph = build_graph(memory)
    save_graph(graph)
