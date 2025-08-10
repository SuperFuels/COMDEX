import csv
from backend.modules.knowledge_graph.knowledge_graph_writer import add_source, link_source

def load_biology_sources(csv_path):
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = row["node_id"]
            source_dict = {
                "tier": row.get("tier", "primary"),
                "ref": row.get("ref", ""),
                "notes": row.get("notes", "")
            }
            add_source(node_id, source_dict)
            if row.get("source_id"):
                link_source(node_id, row["source_id"])