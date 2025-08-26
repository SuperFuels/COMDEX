# backend/modules/symbolnet/wordnet_adapter.py

import logging
from typing import List, Dict, Any, Optional
from nltk.corpus import wordnet as wn

logger = logging.getLogger(__name__)

def query_wordnet(term: str, context: Optional[str] = None, mode: str = "default") -> List[Dict[str, Any]]:
    """
    Query WordNet for synonyms, definitions, and hypernyms of a given term.
    Returns a list of dicts compatible with SymbolNet format.
    """
    results = []
    try:
        logger.info(f"📚 Querying WordNet for term: {term}")
        synsets = wn.synsets(term)

        seen_labels = set()

        for synset in synsets:
            for lemma in synset.lemmas():
                label = lemma.name().replace('_', ' ')
                if label.lower() == term.lower() or label in seen_labels:
                    continue
                seen_labels.add(label)

                results.append({
                    "label": label,
                    "source": "wordnet",
                    "type": "synonym",
                    "description": synset.definition(),
                    "score": 0.6
                })

            for hyper in synset.hypernyms():
                for lemma in hyper.lemmas():
                    label = lemma.name().replace('_', ' ')
                    if label in seen_labels:
                        continue
                    seen_labels.add(label)

                    results.append({
                        "label": label,
                        "source": "wordnet",
                        "type": "hypernym",
                        "description": hyper.definition(),
                        "score": 0.5
                    })

    except Exception as e:
        logger.error(f"❌ WordNet query failed for term '{term}': {e}")
    return results