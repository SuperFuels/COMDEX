---

### 🧾 **backend/modules/wiki_capsules/docs/WIKI_FORMAT_SPEC.md**

```markdown
# Tessaris `.wiki.phn` Format Specification

The `.wiki.phn` file represents a serialized **Wiki Capsule**, 
a read-only semantic entity linked to the Knowledge Graph.

---

## 1. File Header
YAML-like structure defining metadata:
```yaml
meta:
  version: 1.0
  signed_by: Tessaris-Core
  checksum: SHA3-256
  sqi_score: 0.92
  ρ: 0.71
  Ī: 0.83


2. Body Format

lemma: Apple
pos: noun
definitions:
  - A sweet fruit from the apple tree.
examples:
  - She ate a red apple.
synonyms: [fruit, pomaceous]
antonyms: []
entangled_links:
  Nutrition: Lexicon>Health>VitaminC


3. Encoding
	•	UTF-8 encoded, no BOM.
	•	Supports ⊕, ↔, ∇, and other glyphs as valid tokens.

⸻

4. Validation Rules

Rule
Description
Lemma must be capitalized
e.g., “Apple”
Signed by Tessaris-Core
ensures integrity
SHA3-256 checksum
auto-generated
Read-only access enforced
.wiki.phn cannot mutate state


5. Cross-Link Format

Links use the > separator:

Lexicon>Fruit>Apple
Culture>Music>Harmony

6. Security Layer
	•	Verified at load time by safety_layer.py
	•	Rejects unsigned or tampered capsules
	•	Logs all SQI and KG-related events

⸻

7. Example

^wiki_capsule {
meta:
  version: 1.0
  signed_by: Tessaris-Core
  checksum: SHA3-256
lemma: Apple
pos: noun
definitions:
  - A sweet edible fruit produced by an apple tree.
examples:
  - Apple pie is delicious.
synonyms: [fruit, pomaceous]
antonyms: []
entangled_links:
  Culture: Lexicon>Fruit>Symbolism
}

