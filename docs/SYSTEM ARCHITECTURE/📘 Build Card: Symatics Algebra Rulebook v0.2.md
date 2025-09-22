📘 Build Card: Symatics Algebra Rulebook v0.2

🎯 Goal

Extend the Rulebook with physical realism and multi-party quantum constructs, while keeping it compatible with the existing LAW_REGISTRY.
	•	Add wave interference/damping.
	•	Add multi-party entanglement (GHZ/W states).
	•	Add resonance decay envelopes (Q-factor).
	•	Add measurement noise (probabilistic collapse).

⸻

📌 Subtasks

R1. Interference & Damping Models
	•	Define destructive interference at π phase shift.
	•	Add amplitude damping function A(t) = A0 * e^(-γt).
	•	Extend operator set: ⊖ (phase inversion), ↯ (damping).
	•	Add tests: two waves in opposite phase → cancellation.

R2. Multi-party Entanglement
	•	Define GHZ (|000⟩ + |111⟩) / W (equal weight single excitations).
	•	Add ⊗n operator → n-way entanglement.
	•	Extend LAW_REGISTRY: entanglement laws reference multi-party contexts.
	•	Tests:
	•	GHZ: collapse one qubit → others collapse consistently.
	•	W: collapse one qubit → others remain partially entangled.

R3. Resonance Decay (Q-Factor)
	•	Define quality factor Q = ω₀ / Δω.
	•	Add resonance envelope law:

A(t) = A0 * cos(ω₀t) * e^(-t/(2Q))

	•	Operator: ℚ (resonant quality).
	•	LAW_REGISTRY entry: “resonance law”.
	•	Tests: simulate two Q values and compare decay rates.

R4. Measurement Noise Model
	•	Define probabilistic collapse: measurement → true state with prob (1–ε), error state with prob ε.
	•	Add operator: ε (noise).
	•	LAW_REGISTRY entry: “measurement noise law”.
	•	Tests: Monte Carlo runs → distribution matches expected error rate.

⸻

📌 Implementation Plan

File: backend/modules/symatics/symatics_rulebook.py
	•	Add new operator entries: ⊖, ↯, ⊗n, ℚ, ε.
	•	Add law definitions (dicts with name, operator, logic, tests).
	•	Extend LAW_REGISTRY with v0.2 entries.
	•	Tag all new entries with version: "0.2".

⸻

⚡ Design Decisions / Open Questions
	•	Should damping/decay be modeled as symbolic-only (↯) or numeric (with γ values)?
👉 Recommendation: support both, start with symbolic.
	•	For GHZ/W, do we store entanglement as tensor state or abstract law?
👉 Recommendation: abstract law, with hooks for tensor backend later.
	•	Noise: do we simulate at container level or operator level?
👉 Recommendation: operator-level first (probabilistic ε).

⸻

✅ Test Criteria
	•	LAW_REGISTRY contains all new v0.2 entries.
	•	Unit tests confirm:
	•	Interference cancellation works.
	•	Entanglement laws generate correct collapse behavior.
	•	Resonance Q-factor law produces correct envelope.
	•	Noise operator produces expected Monte Carlo distribution.

⸻

📊 Status in Roadmap
	•	A1–A6 ✅/🟢
	•	A4 → upgraded to Rulebook v0.2 (this task).
	•	A5 (Engine) will consume these new laws.
	•	A6 (Calculus) builds on top of damping/decay.

⸻

⚡ Next step:
👉 Draft symatics_rulebook.py v0.2 update with these new operators and laws.
