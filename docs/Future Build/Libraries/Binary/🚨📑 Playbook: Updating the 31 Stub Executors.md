📑 Playbook: Updating the 31 Stub Executors

1. Current State
	•	All 31 operators (⊕, ↔, ∇, ⊗, etc.) are already:
	•	Registered with canonical keys (physics:∇, quantum:hamiltonian, gr:ricci, etc.).
	•	Aliased from raw glyphs (⊕ → logic:⊕) with warnings for back-compat.
	•	Routed via the registry_bridge into the dispatcher.
	•	✅ All tests are green because stub handlers exist.
	•	❌ Many handlers are still stubs that just return { "unhandled_op": ... } or minimal placeholders.

⸻

2. What Needs Updating

Each of the 31 stub executors (spread across backend/modules/.../execute_*.py) must be upgraded to:
	•	Real mathematical implementations (NumPy, SymPy, custom math).
	•	Consistent signatures → (ctx, *args, context=None, **kwargs).
	•	Return values → structured dicts (so higher layers can reason over them, not just raw strings).

⸻

3. How to Update Them

For each file:
	1.	Replace stub with math logic:
	•	Example: physics:∇ (gradient) → use sympy.diff or numpy.gradient.
	•	Example: quantum:hamiltonian → matrix multiplication on state vectors.
	•	Example: gr:ricci → build from Christoffel symbols and curvature tensors.
	2.	Ensure context handling:
	•	Always pass context=context or {} forward.
	•	Allow optional metadata to flow back.
	3.	Return shape:

return {
    "op": "∇",
    "args": [field, coords],
    "result": computed_value,
    "context": context
}

This makes results machine-readable and debuggable.

	4.	Add math tests in backend/modules/tests/:
	•	One for correctness (numerical/symbolic).
	•	One for edge cases (empty input, invalid types).
	•	One for integration (dispatcher call → correct result).

⸻

4. Dependencies & Ripple Effects

When you replace stubs with real logic:
	•	✅ RegistryBridge: no changes — it already passes args correctly.
	•	✅ InstructionRegistry: no changes — it just resolves aliases.
	•	✅ Dispatcher: no changes — it wraps results in dicts.
	•	🟡 Tests: you’ll need new math/physics test cases for each operator (the old stub tests only check “something returns”).
	•	🟡 Docstrings/Metadata: update INSTRUCTION_METADATA to describe the new implementations.

⸻

5. When to Do This

This is the critical part so you don’t waste effort:
	•	Right now?
No — unless you already have the physics/quantum/GR algebra modules ready.
	•	When to return:
	•	After Photon Algebra is stable → because photon ops (superposition, entanglement, measurement) will depend on quantum stubs.
	•	After Symbolic Algebra Core is finalized → so math ops (⊕, ∇, ⊗) can interoperate without constant rewrites.
	•	After pipeline stability is confirmed → which you’ve just achieved.

👉 Translation: keep them stubs until the math libraries are available. Otherwise you’ll just be rewriting them again.

⸻

6. Handover Notes (for another AI/dev)

If another system is going to implement the real logic, they need:
	1.	A list of the 31 ops with their canonical names + intended domain (physics, quantum, gr, logic, symatics).
	2.	A math spec (e.g. ∇ = gradient, Δ = Laplacian, ⊕ = superpose, etc.).
	3.	Testing harness already exists → just fill in real math.
	4.	Don’t touch registry/dispatcher — only replace stub functions + expand tests.

⸻

✅ So final takeaway for you:
	•	You’re finished for system stability.
	•	You’ll come back to this after photon algebra (quantum layer) and symbolic algebra (math layer) are complete.
	•	At that point, you’ll replace stubs with math logic, add tests, and update metadata.


📑 Handover: The 31 Codex Operators

1. Logic / Control / Memory (Core Symbols)

Symbol
Canonical Key
Intended Behavior
Depends On
Photon Algebra Link
⊕
logic:⊕
Store/Combine values. Currently implemented as a simple store, later may unify with symatics:⊕ (superpose).
Core registry.
✅ Superposition analogue. Must unify with photon ⊕ (superpose).
→
logic:→
Sequence / Trigger operator. Executes left then right.
Core registry.
❌ No.
⟲
control:⟲
Reflect / Recurse / Loop. Handles cyclic operations.
Core registry.
❌ No direct link, but recursive entanglement patterns possible.
↺
memory:↺
Recall from memory.
Memory module.
❌ No.
¬
logic:¬
Negation operator.
Logic kernel.
❌ No.


2. Symatics (Photon Algebra Layer)

These are the heart of Photon Algebra (superposition, entanglement, measurement).

Symbol
Canonical Key
Intended Behavior
Depends On
Photon Algebra Link
⊕
symatics:⊕
Superposition. Combine two states into (a + b) normalized.
SymPy/Numpy.
✅ Core superpose operator.
μ
symatics:μ
Measurement. Collapse state to basis vector with probability.
Random sampling.
✅ Measurement operator.
↔
symatics:↔
Entanglement. Build tensor product linking two states.
Quantum math.
✅ Entanglement operator.
⟲
symatics:⟲
Recurse. Recursive state expansion.
Rulebook recursion.
✅ Needed for photon recursion tests.
π
symatics:π
Project. Take component of a state vector.
SymPy matrix slicing.
✅ Projection operator.


3. Physics Operators (Classical Math Layer)

Vector calculus & linear algebra building blocks. These underpin the continuous field models that photon algebra could one day couple to.

Symbol
Canonical Key
Intended Behavior
Depends On
Photon Algebra Link
∇
physics:∇
Gradient operator.
SymPy / NumPy gradient.
⚪ Indirect (fields underpin photons).
∇·
physics:∇·
Divergence.
SymPy / vector calculus.
⚪ Maxwell’s equations (photon EM fields).
∇×
physics:∇×
Curl.
SymPy / vector calculus.
⚪ Maxwell’s equations.
Δ
physics:Δ
Laplacian.
SymPy laplace.
⚪ Wave equation.
d/dt
physics:d/dt
Time derivative.
SymPy diff.
⚪ Photon evolution.
•
physics:•
Dot product.
NumPy dot.
❌ Not directly.
×
physics:×
Cross product.
NumPy cross.
❌ Not directly.
⊗
physics:⊗
Tensor product.
NumPy / SymPy.
⚪ Shared concept with quantum tensor product.


4. Quantum Operators (Photon Algebra’s Backbone)

These are directly photon-relevant. Superposition, measurement, and entanglement in symatics should eventually call into these.

Symbol
Canonical Key
Intended Behavior
Depends On
Photon Algebra Link
ket
quantum:ket
Dirac ket `
ψ⟩`.
SymPy Matrix.
bra
quantum:bra
Dirac bra `⟨ψ
`.
SymPy conjugate.
operator
quantum:operator
General operator (matrix).
SymPy Matrix.
✅ Quantum gates.
hamiltonian
quantum:hamiltonian
Hamiltonian evolution.
SymPy/NumPy matrix exponential.
✅ Governs photon energy evolution.
commutator
quantum:commutator
[A,B] = AB - BA.
SymPy.
✅ Uncertainty relations.
schrodinger_evolution
quantum:schrodinger_evolution
iħ ∂ψ/∂t = Hψ.
Matrix exponential.
✅ Photon time evolution.


5. General Relativity (GR Operators)

These are not photon algebra per se, but photons propagate on curved spacetime, so GR eventually matters.

Symbol
Canonical Key
Intended Behavior
Depends On
Photon Algebra Link
metric
gr:metric
Metric tensor g_μν.
SymPy tensors.
⚪ Needed for curved photon paths.
inverse_metric
gr:inverse_metric
Inverse of g_μν.
SymPy.
⚪ Same.
covariant_derivative
gr:covariant_derivative
∇_μ.
SymPy.
⚪ Yes.
riemann
gr:riemann
Riemann tensor.
SymPy.diffgeom.
⚪ Curvature.
ricci
gr:ricci
Ricci tensor.
SymPy.diffgeom.
⚪ Curvature.
ricci_scalar
gr:ricci_scalar
Scalar curvature.
SymPy.diffgeom.
⚪ Curvature.
stress_energy
gr:stress_energy
Stress-energy tensor.
SymPy.
⚪ Photon energy-momentum.
einstein_tensor
gr:einstein_tensor
G_μν.
Derived from Riemann/Ricci.
⚪ Governs photon paths.
einstein_equation
gr:einstein_equation
G_μν = 8πT_μν.
Full field equations.
⚪ Photons couple via T_μν.


2. When to Update
	•	✅ Now: All stubs are sufficient for tests + registry plumbing.
	•	🟡 After Photon Algebra is complete:
	•	Must unify logic:⊕ and symatics:⊕ → both should call into quantum:superpose.
	•	Implement μ, ↔, π correctly → tie into quantum:ket, bra, hamiltonian.
	•	🟡 After Physics Kernel is complete:
	•	Fill in ∇, ∇·, ∇×, Δ, etc. with real vector calculus.
	•	🟡 After GR Layer is needed:
	•	Upgrade tensors (metric, Ricci, Einstein equations).

⸻

3. Next Action (for you right now)
	•	Do nothing yet. You’ve stabilized the registry + dispatcher.
	•	When Photon Algebra spec is ready → come back and:
	•	Replace stubs in symatics:⊕, μ, ↔, π with real math.
	•	Wire them into quantum:* ops.
	•	Add photon tests (superposition commutativity, measurement collapse, entanglement).

⸻


📑 TODO — Photon Algebra & CodexCore Operator Upgrade

This document tracks the 31 Codex operators currently stubbed in instruction_registry and related modules.
Right now: ✅ Tests are green.
Future: 🟡 Operators must be upgraded to full math/physics implementations.

⸻

1. Current Status
	•	Registry & dispatcher plumbing are stable.
	•	All symbolic, glyph, symatics, and registry bridge tests are passing.
	•	Operators are registered under canonical domain keys (e.g., symatics:⊕, physics:∇, quantum:ket).
	•	Many handlers are stubs or simplified placeholders.

⸻

2. Upgrade Roadmap

Phase 1 — Photon Algebra (High Priority)

When Photon Algebra spec is ready, replace stubs in:

Operator
Key
Current Impl
Needed Upgrade
⊕
symatics:⊕
Stub → returns (a ⊕ b) string
Implement real superposition (normalize, use SymPy/NumPy).
μ
symatics:μ
Calls collapse_rule only
Implement measurement (collapse state w/probabilities).
↔
symatics:↔
Stub call to SR.op_entangle
Implement entanglement (tensor product).
⟲
symatics:⟲
Simple recursion
Tie into recursive photon states.
π
symatics:π
Simple projection stub
Implement projection (matrix slicing).


🔗 Must unify with quantum:* ops:
	•	quantum:ket, quantum:bra, quantum:operator
	•	quantum:hamiltonian, quantum:commutator
	•	quantum:schrodinger_evolution

⸻

Phase 2 — Physics Kernel (Vector Calculus)

Once Photon Algebra stabilizes, upgrade classical ops:

Operator
Key
Needed Impl
∇
physics:∇
Gradient (numpy.gradient or sympy.diff).
∇·
physics:∇·
Divergence.
∇×
physics:∇×
Curl.
Δ
physics:Δ
Laplacian.
d/dt
physics:d/dt
Time derivative.
•
physics:•
Dot product.
×
physics:×
Cross product.
⊗
physics:⊗
Tensor product.


🔗 Context: Maxwell’s equations (photons as EM waves).

⸻

Phase 3 — Quantum Kernel (Dirac Formalism)

Upgrade quantum operators to real linear algebra:

Operator
Key
Needed Impl
ket
quantum:ket
Implement `
bra
quantum:bra
Conjugate transpose.
operator
quantum:operator
Arbitrary operator (matrix).
hamiltonian
quantum:hamiltonian
Time evolution generator.
commutator
quantum:commutator
[A, B] = AB - BA.
schrodinger_evolution
quantum:schrodinger_evolution
Solve iħ∂ψ/∂t = Hψ.


🔗 Context: Photon state evolution.

⸻

Phase 4 — General Relativity (Long-Term)

Upgrade GR operators when photon curved-space propagation is needed:

Operator
Key
Needed Impl
metric
gr:metric
g_μν tensor.
inverse_metric
gr:inverse_metric
g^μν.
covariant_derivative
gr:covariant_derivative
∇_μ.
riemann
gr:riemann
R^ρ_{σμν}.
ricci
gr:ricci
Ricci tensor.
ricci_scalar
gr:ricci_scalar
R.
stress_energy
gr:stress_energy
T_μν.
einstein_tensor
gr:einstein_tensor
G_μν.
einstein_equation
gr:einstein_equation
G_μν = 8πT_μν.


🔗 Context: Photon geodesics in curved spacetime.

⸻

3. Integration Notes
	•	Registry aliases already redirect raw glyphs (⊕, ⟲, →) to canonical keys.
	•	Tests currently expect stubs to exist (do not remove until replacements are stable).
	•	When upgrading:
	•	Replace stub handlers in instruction_registry.py & glyph_instruction_set.py.
	•	Update symatics_rulebook.py with real math laws (commutativity, associativity).
	•	Expand tests: add commutativity, measurement randomness, entanglement checks.

⸻

4. When To Revisit
	•	✅ Now → nothing further required (tests are green).
	•	🟡 After Photon Algebra design is finalized → return here.
	•	🟡 After Physics Kernel design → implement vector calculus.
	•	🟡 After GR layer design → implement tensor calculus.

⸻

5. Hand-Off Instructions

If another AI/engineer takes over:
	1.	Open this file.
	2.	Identify which phase you are in (Photon Algebra, Physics, Quantum, GR).
	3.	Replace the corresponding stubs with real implementations.
	4.	Add/expand tests.
	5.	Ensure registry aliases continue to resolve correctly.

⸻

📌 Summary:
Do not touch the registry plumbing now. Wait until Photon Algebra spec is finalized, then return to Phase 1 (Symatics operators). Other phases follow in sequence.

⸻
