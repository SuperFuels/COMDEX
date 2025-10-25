from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule
from backend.modules.wiki_capsules.foundations.wiki_serializer import save_wiki_capsule
from pathlib import Path

apple = make_capsule(
    "apple", "noun",
    ["A round fruit of a tree of the rose family."],
    ["He ate a red apple."],
    synonyms=["pome"],
    entangled_links={"Fruits": ["Banana", "Cherry"]}
)

save_wiki_capsule(apple, Path("data/knowledge/lexicon/Lexicon_Apple.wiki.phn"))
print("✅ Wiki capsule created successfully.")