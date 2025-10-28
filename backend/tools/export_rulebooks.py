# ================================================================
# 📤 export_rulebooks.py — export all rulebooks to .dc containers
# ================================================================
import logging
from backend.modules.aion_cognition.rulebook_index import RuleBookIndex

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    index = RuleBookIndex()
    path = index.export_all()
    print(f"✅ Exported rulebooks → {path}")