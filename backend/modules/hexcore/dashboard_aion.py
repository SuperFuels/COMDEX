import json
import yaml
from flask import Flask, jsonify, request

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

app = Flask(__name__)

MEMORY_FILE = "backend/modules/hexcore/memory.json"
SOUL_LAWS_FILE = "backend/modules/hexcore/soul_laws.yaml"
GOVERNANCE_FILE = "backend/modules/hexcore/governance_config.yaml"

@app.route("/aion/status", methods=["GET"])
def get_status():
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
    score = sum(1 for entry in memory if entry.get("emotion") != "neutral")
    return jsonify({"growth_score": score, "memory_count": len(memory)})

@app.route("/aion/memory", methods=["GET"])
def get_memory():
    with open(MEMORY_FILE, "r") as f:
        return jsonify(json.load(f))

@app.route("/aion/laws", methods=["GET"])
def get_soul_laws():
    with open(SOUL_LAWS_FILE, "r") as f:
        return jsonify(yaml.safe_load(f))

@app.route("/aion/governance", methods=["GET"])
def get_governance():
    with open(GOVERNANCE_FILE, "r") as f:
        return jsonify(yaml.safe_load(f))

@app.route("/aion/update_emotion", methods=["POST"])
def update_emotion():
    data = request.get_json()
    if "emotion" not in data:
        return jsonify({"error": "Missing emotion value"}), 400

    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
    if not memory:
        return jsonify({"error": "No memory to update"}), 404

    memory[-1]["emotion"] = data["emotion"]
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

    return jsonify({"message": "Emotion updated", "latest": memory[-1]})

if __name__ == "__main__":
    app.run(debug=True, port=5050)

