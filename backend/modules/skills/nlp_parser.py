import os
import openai
from dotenv import load_dotenv
from modules.hexcore.memory_engine import MemoryEngine

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class NLPParser:
    def __init__(self):
        self.memory = MemoryEngine()

    def parse_and_store(self, sentence):
        prompt = f"Extract entities and intent from: '{sentence}'\nFormat as JSON with 'entities' and 'intent' keys."

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You extract structured data from natural language."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.strip()
        print("\n🔍 Parsed NLP Output:\n", result)

        self.memory.store({
            "label": "nlp_extraction",
            "content": result
        })
        print("🧠 Saved to MemoryEngine.")

if __name__ == "__main__":
    parser = NLPParser()
    parser.parse_and_store("Find me a supplier in Vietnam for 5 tonnes of organic cacao beans.")