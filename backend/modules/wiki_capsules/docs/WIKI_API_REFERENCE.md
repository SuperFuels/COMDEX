---

### 🧠 **backend/modules/wiki_capsules/docs/WIKI_API_REFERENCE.md**

```markdown
# Tessaris Wiki Capsule API Reference

Comprehensive developer reference for all backend modules under:
`backend/modules/wiki_capsules/`

---

## 📚 Foundations

### `wiki_capsule_schema.py`
Defines the `WikiCapsule` dataclass:
```python
@dataclass
class WikiCapsule:
    lemma: str
    pos: str
    definitions: list
    examples: list
    synonyms: list = field(default_factory=list)
    antonyms: list = field(default_factory=list)
    entangled_links: dict = field(default_factory=dict)

wiki_serializer.py
	•	serialize_to_phn(capsule) → returns .wiki.phn text.
	•	save_wiki_capsule(capsule, path) → persists capsule.

⸻

🔗 Integration Layer

kg_query_extensions.py
	•	add_capsule_to_kg(capsule, domain) → register in KG.
	•	get_wiki(lemma, domain) → fetch + resolve capsule.
	•	list_domain(domain) → enumerate entries.

wiki_importer.py
	•	Converts JSON dictionaries into .wiki.phn capsules.
	•	Saves to /data/knowledge/<domain>/.

⸻

📘 Photon Hooks

wiki_plugin.py
	•	Glyph handler for 📚 import.
	•	Fetches .wiki.phn capsule via get_wiki() and returns structured data.

⸻

🔐 Security Layer

safety_layer.py
	•	verify_signature(capsule) → confirm checksum + signers.
	•	enforce_whitelist(domain, lemma) → restrict imports.
	•	apply_sandbox_policy(file_path) → enforce read-only access.
	•	audit_event(event, meta) → log runtime KG/SQI actions.

⸻

🔍 Dev Tools & Search

search_api.py
	•	search(term) → exact + fuzzy match over KG.
	•	search_by_synonym(word) → synonym lookup.

sci_autocomplete_plugin.py
	•	IDE integration for Capsule lemma completion.

graph_explorer_ui.py
	•	Graphical exploration interface for KG visualization and wormhole navigation.

⸻

🧩 Validation & Maintenance

wiki_linter.py
	•	Verifies .wiki.phn grammar, metadata, and checksum.

reference_validator.py
	•	Ensures all entangled links resolve correctly.

maintenance_jobs.py
	•	Automated cleanup, integrity validation, and pruning.

⸻

⚡ Runtime & Resonance

photon_executor_extension.py
	•	Enhanced runtime loader for .phn and .ptn.

wiki_resonance_sync.py
	•	Harmonizes SQI metrics with Wiki metadata.

⸻

📊 Test Coverage SummaryModule
Tests
Status
Foundations
✅ test_create_capsule.py
Passed
KG Integration
✅ test_kg_query.py
Passed
Photon Plugin
✅ test_wiki_plugin.py
Passed
Security
✅ test_safety_layer.py
Passed
Search Tools
✅ test_search_api.py
Passed
Validation
✅ test_linter.py, test_reference.py
Passed
