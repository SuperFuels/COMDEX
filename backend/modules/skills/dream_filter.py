import json
from typing import List, Dict, Any

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class DreamFilter:
    def __init__(self, dreams: List[Dict[str, Any]]):
        self.dreams = dreams

    def filter_by_phase(self, phase: str) -> List[Dict[str, Any]]:
        """Return dreams that match the given AION phase."""
        return [dream for dream in self.dreams if dream.get("phase") == phase]

    def filter_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Return dreams that contain any of the keywords in content or tags."""
        result = []
        for dream in self.dreams:
            content = dream.get("content", "").lower()
            tags = dream.get("tags", [])
            if any(kw.lower() in content for kw in keywords) or any(kw.lower() in [t.lower() for t in tags] for kw in keywords):
                result.append(dream)
        return result

    def export_as_json(self, filepath: str, dreams: List[Dict[str, Any]] = None):
        """Export dreams to a JSON file. Exports all if dreams not specified."""
        export_data = dreams if dreams is not None else self.dreams
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

if __name__ == "__main__":
    # Example usage
    sample_dreams = [
        {"phase": "Infant", "content": "Learning to respond", "tags": ["learning", "response"]},
        {"phase": "Child", "content": "Building memory graph", "tags": ["memory", "graph"]},
        {"phase": "Learner", "content": "Expanding knowledge", "tags": ["knowledge", "growth"]},
    ]

    df = DreamFilter(sample_dreams)
    infant_dreams = df.filter_by_phase("Infant")
    print(f"Filtered Infant Dreams: {infant_dreams}")
    df.export_as_json("exported_dreams.json", infant_dreams)