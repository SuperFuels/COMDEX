from sentence_transformers import SentenceTransformer, util

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# 🔄 Global model instance
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("./models/all-MiniLM-L6-v2", local_files_only=True)
    return _model

def get_embedding(text):
    model = get_model()
    return model.encode(text, convert_to_tensor=True)

def cosine_sim(a, b):
    return util.pytorch_cos_sim(a, b).item()