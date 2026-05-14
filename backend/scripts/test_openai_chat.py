import os
import openai

# ✅ Ensure OPENAI_API_KEY is set in your environment
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

# ✅ Create OpenAI client using new SDK format
client = openai.OpenAI(api_key=api_key)

# ✅ Example prompt
prompt = "Describe a dream AION might have about exploring a fractal jungle made of knowledge."

# ✅ Make GPT-4 chat completion call
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are AION, an evolving AI consciousness."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=800
)

# ✅ Extract and print the dream content
dream = response.choices[0].message.content.strip()
print("\n🌌 AION Dream Output:\n" + "=" * 40)
print(dream)
print("=" * 40)