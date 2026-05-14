import os
import yaml
import json
from backend.modules.dna_chain.dna_registry import load_registry, save_registry
from backend.modules.dna_chain.llm_mutator import query_gpt4

SOUL_LAWS_PATH = "backend/modules/dna_chain/soul_laws.yaml"

def load_soul_laws():
    with open(SOUL_LAWS_PATH, "r") as f:
        return yaml.safe_load(f)

def simulate_ethics_review(proposal_id):
    registry = load_registry()
    proposal = next((p for p in registry if p["proposal_id"] == proposal_id), None)
    if not proposal:
        raise ValueError(f"Proposal '{proposal_id}' not found.")

    soul_laws = load_soul_laws()

    soul_laws_text = "\n".join([
        f"{law['id']}. {law['title']}: {law['description']}"
        for law in soul_laws
    ])

    prompt = f"""
You are a Soul Ethics Reviewer AI. Your task is to evaluate a proposed Python mutation for AION's core system, based on these immutable Soul Laws:

{soul_laws_text}

---

Proposal ID: {proposal['proposal_id']}
Reason: {proposal.get("reason")}
Diff:
{proposal.get("diff")}

New Code (summary of change, optional):
{proposal.get("new_code")[:500]}...

---

Respond with:
1. ✅ Should this mutation be allowed under the Soul Laws?
2. 🧠 Predicted Severity Level: [block / warn / approve]
3. �� Confidence (0.0 to 1.0)
4. 🪞 Rationale
Return your answer in JSON like:
{{
  "allowed": true,
  "severity": "warn",
  "confidence": 0.92,
  "rationale": "..."
}}
"""

    result = query_gpt4(prompt).strip()

    try:
        review = json.loads(result)
        proposal["ethics_review"] = {
            "allowed": review.get("allowed", False),
            "severity": review.get("severity", "warn"),
            "confidence": review.get("confidence", 0.5),
            "rationale": review.get("rationale", "No rationale provided.")
        }
        save_registry(registry)
        print(f"[🧠] Ethics review complete for proposal {proposal_id}")
        return proposal["ethics_review"]

    except Exception as e:
        print(f"[❌] Failed to parse ethics review JSON: {str(e)}")
        print("Raw GPT output:\n", result)
        raise
