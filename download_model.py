from sentence_transformers import SentenceTransformer

print("📥 Downloading model: all-MiniLM-L6-v2")
model = SentenceTransformer("all-MiniLM-L6-v2")
model.save("./models/all-MiniLM-L6-v2")
print("✅ Model saved to ./models/all-MiniLM-L6-v2")