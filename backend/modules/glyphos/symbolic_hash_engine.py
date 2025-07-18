import hashlib

def symbolic_hash(glyph):
    glyph_str = glyph.strip().encode('utf-8')
    return hashlib.sha256(glyph_str).hexdigest()

def is_duplicate(glyph, known_hashes):
    h = symbolic_hash(glyph)
    return h in known_hashes
