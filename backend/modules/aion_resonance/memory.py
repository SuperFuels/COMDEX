from backend.modules.aion_resonance.resonance_lexicon_store import RESONANCE_LEXICON

def store_phi_mapping(intent, phi):
    return RESONANCE_LEXICON.put(intent, phi)
