🧩 CodexLang Cleanup & Instruction System Design Notes

Last updated: 2025-09-29

This document summarizes the current state of CodexLang instruction cleanup, canonicalization, and rewrite pipeline.
It is intended as a reference for why certain changes were made, where the main registries live, and how the system stays consistent.

⸻

✅ Core Components

1. Canonical Ops Registry
	•	File: backend/modules/codex/canonical_ops.py
	•	What: Maps raw glyph symbols (⊕, ∇, ⟲) to canonical, domain-tagged keys (logic:⊕, math:∇, control:⟲).
	•	Why:
	•	Removes symbol collisions (e.g. ⊗ exists in logic, physics, and symatics).
	•	Ensures all downstream systems (executor, translators, docs) speak the same “canonical” language.
	•	Extra: Also carries OP_METADATA → descriptions, categories, symbols for doc generation.

⸻

2. Symatics → Codex Rewriter
	•	File: backend/symatics/symatics_to_codex_rewriter.py
	•	What: Translates Symatics-specific operators into CodexLang canonical form.
	•	Why: Symatics introduced its own ops (cancel, damping, resonance, ⊗_s). These need to be unified with the Codex pipeline without forking execution logic.
	•	Notes: Currently a stub → can be extended with explicit rewrite rules.

⸻

3. CodexLang Rewriter
	•	File: backend/modules/codex/codexlang_rewriter.py
	•	What: Canonicalizes any instruction tree ops into their domain-tagged equivalents using the registry.
	•	Why: Ensures no raw ⊕ or ∇ sneak into execution — only logic:⊕, math:∇, etc.
	•	Test Hook: Can be monkeypatched in unit tests to verify rewrite flow.

⸻

4. Instruction Metadata Bridge
	•	File: backend/modules/codex/canonical_ops.py (with OP_METADATA)
	•	What: Central place where operator descriptions, categories, and symbols live.
	•	Why:
	•	Provides one source of truth for documentation.
	•	Avoids drift between docs, executor, and symbolic engines.
	•	Usage: Consumed by auto-doc builder.

⸻

5. Instruction Reference Builder
	•	File: docs/CodexLang_Instruction/instruction_reference_builder.py
	•	What: Generates instruction_reference.md from OP_METADATA.
	•	Why: Auto-docs avoid manual drift and make operator set transparent.
	•	Command:


PYTHONPATH=. python docs/CodexLang_Instruction/instruction_reference_builder.py

	•	Output: docs/CodexLang_Instruction/instruction_reference.md

⸻

6. CodexExecutor Pipeline (Updated)
	•	File: backend/modules/codex/codex_executor.py
	•	Changes Made:
	•	Added rewrite stage (symatics → codex, then canonicalization) before validation.
	•	Added test_mode=True flag to allow unit tests to stop after rewrite (no heavy validation).
	•	Why:
	•	Ensures all execution paths run on canonical keys.
	•	Keeps unit tests lightweight and focused.

⸻

7. Integration & Tests
	•	Key Tests:
	•	backend/modules/tests/test_executor_rewrites_ops.py → verifies executor rewrite stage.
	•	backend/modules/tests/test_executor_pipeline.py → verifies end-to-end pipeline (glyph → translator → executor).
	•	Why: Protects against regressions (e.g. skipping canonicalization).
	•	Notes: Tests rely on monkeypatching CodexLangRewriter.canonicalize_ops to confirm call path.

⸻

🚦 Current Workflow
	1.	Glyph enters executor → may be raw (⊕) or domain-tagged.
	2.	Symatics Rewriter translates Symatics ops if applicable.
	3.	CodexLang Rewriter enforces canonical domain keys (logic:⊕).
	4.	Validation checks theorem/logic completeness (skipped if test_mode).
	5.	Execution handled by CodexExecutor / downstream engines.
	6.	Docs always synced with operator registry (OP_METADATA).

⸻

📌 Why This Matters
	•	Prevents operator collisions (⊗ across multiple domains).
	•	Establishes a single registry for all operator metadata.
	•	Enables auto-docs and tests that guard rewrite behavior.
	•	Provides a clean onramp for new domains (just update canonical_ops.py and regenerate docs).

⸻

📍 Where to Look (Cheat Sheet)
	•	Canonical registry: backend/modules/codex/canonical_ops.py
	•	Rewriters:
	•	Symatics → Codex: backend/symatics/symatics_to_codex_rewriter.py
	•	Canonicalizer: backend/modules/codex/codexlang_rewriter.py
	•	Executor: backend/modules/codex/codex_executor.py
	•	Docs:
	•	Builder: docs/CodexLang_Instruction/instruction_reference_builder.py
	•	Output: docs/CodexLang_Instruction/instruction_reference.md
	•	Tests: backend/modules/tests/test_executor_*


⚖️ Collision Resolution Overview

Most CodexLang symbols are unique to their domain and map directly to a canonical operator (e.g., ¬, ∧, ∨, H, ⟨ψ|, ψ⟩, cancel, resonance).
These do not require disambiguation and pass straight through the translator.

Only a handful of “troublemaker” symbols appear in multiple domains and need the collision resolver:


Symbol										Possible Domains								Notes
⊗											logic, physics, symatics						Tensor / product ambiguity
⊕											logic, quantum									XOR-like vs quantum addition
↔											logic, quantum									Equivalence vs quantum bidirection
∇											math (reserved for expansion)					May overlap in future domains
≈ / ~										photon											Aliased forms of wave equivalence



The resolver works as a safety net:
	•	If the symbol is explicitly tagged (e.g., ⊗_p → physics:⊗), no guessing is needed.
	•	If the symbol is bare/ambiguous (e.g., just ⊗), the resolver applies priority rules to pick the most likely domain.

👉 This way, you only pay the cost of collision resolution for these few special cases.
👉 Everything else stays simple and direct.

⸻

