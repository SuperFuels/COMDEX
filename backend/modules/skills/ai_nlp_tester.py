import os
from dotenv import load_dotenv
import openai
from backend.modules.aion.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class NLPTester:
    def __init__(self):
        self.milestones = MilestoneTracker()
        # 🔐 Correct milestone check: should be "language_understanding"
        if not self.milestones.is_unlocked("language_understanding"):
            print("❌ ai_nlp milestone not unlocked (language_understanding required).")
            exit()

    def run(self):
        prompt = (
            "Extract the entities and intent from this sentence: "
            "'Find me a supplier in Vietnam for 5 tonnes of organic cacao beans.'"
        )
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI specialized in language parsing and understanding."},
                    {"role": "user", "content": prompt}
                ]
            )
            output = response.choices[0].message.content.strip()
            print("\n🧠 NLP Response:\n" + output)
        except Exception as e:
            print(f"⚠️ Error during NLP test: {e}")

if __name__ == "__main__":
    NLPTester().run()