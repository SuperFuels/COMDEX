from backend.modules.symbolnet.symbolnet_loader import get_semantic_vector
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph
from backend.modules.symbolic.hst.hst_semantic_scoring import semantic_distance, concept_match

def test_scoring():
    # Create mock glyphs
    g1 = SymbolGlyph(label="dog")
    g2 = SymbolGlyph(label="cat")
    g3 = SymbolGlyph(label="apple")

    # Print vectors
    print("Vector for 'dog':", get_semantic_vector("dog"))
    print("Vector for 'cat':", get_semantic_vector("cat"))
    print("Vector for 'apple':", get_semantic_vector("apple"))

    # Semantic distance
    print("\nDistance(dog, cat):", semantic_distance(g1, g2))
    print("Distance(dog, apple):", semantic_distance(g1, g3))

    # Concept match to known vector
    concept_vec = get_semantic_vector("animal")
    print("\nMatch(dog, animal):", concept_match(g1, concept_vec))
    print("Match(apple, animal):", concept_match(g3, concept_vec))

if __name__ == "__main__":
    test_scoring()